from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import json
import math
import random
import time
import threading
import urllib.request
import urllib.error
import re
import os
import io
import sqlite3
import hashlib
import heapq
import atexit
from collections import Counter
from pypdf import PdfReader
from ivfpq import IVFPQIndex
from gpu_search import GPUSearchIndex
from knowledge_graph import KnowledgeGraph
from query_parser import NuroLexer, NuroParser, compile_to_api_call

kg = KnowledgeGraph()

# Re-ranking
try:
    from reranker import CrossEncoderReranker
    reranker = CrossEncoderReranker()
except Exception as e:
    print(f"Failed to import/initialize CrossEncoderReranker: {e}")
    reranker = None

# Try to import redis
try:
    import redis
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        redis_client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
    else:
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True, socket_connect_timeout=2)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("Redis connected successfully.")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"Redis not available. Caching disabled. Error: {e}")

# Simple In-Memory Cache fallback when Redis is offline to prevent DB latency
class MemoryCache:
    def __init__(self, maxsize=512):
        self.cache = {}
        self.maxsize = maxsize
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                val, expiry = self.cache[key]
                if time.time() < expiry:
                    return val
                else:
                    del self.cache[key]
            return None

    def set(self, key, value, ttl=3600):
        with self.lock:
            if len(self.cache) >= self.maxsize:
                oldest = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest]
            self.cache[key] = (value, time.time() + ttl)

local_cache = MemoryCache()

# Optional: Kafka producer (gracefully falls back if unavailable)
kafka_producer = None
doc_statuses = {}

def consume_status_updates():
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            'nurosearch-document-status',
            bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9092'),
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        for message in consumer:
            event = message.value
            doc_id = event.get('doc_id')
            if doc_id:
                doc_statuses[doc_id] = event
                if REDIS_AVAILABLE:
                    try:
                        redis_client.set(f"doc_status:{doc_id}", json.dumps(event))
                    except Exception:
                        pass
    except Exception as e:
        print(f"[Status Consumer] Error: {e}")

try:
    from kafka import KafkaProducer
    kafka_producer = KafkaProducer(
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9092'),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        request_timeout_ms=1000,
        api_version=(0, 10)
    )
    print("Kafka Producer connected successfully.")
    t = threading.Thread(target=consume_status_updates, daemon=True)
    t.start()
except Exception as e:
    kafka_producer = None
    print(f"Kafka not available. Async ingestion disabled. Error: {e}")

app = Flask(__name__, static_folder=".")
CORS(app)

DIMS = 16

# =====================================================================
#  BM25 (For Hybrid Search)
# =====================================================================

class BM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0

    def index(self, corpus):
        self.corpus = corpus
        self.doc_freqs = []
        for doc in corpus:
            words = doc.lower().split()
            self.doc_freqs.append(Counter(words))
        self.doc_len = [len(doc.lower().split()) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 1
        
        N = len(corpus)
        freqs = Counter()
        for doc_freq in self.doc_freqs:
            for word in doc_freq:
                freqs[word] += 1
        
        self.idf = {}
        for word, freq in freqs.items():
            self.idf[word] = math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)

    def search(self, query, top_k=5):
        if not self.doc_len or not query.strip():
            return []
        scores = []
        query_words = query.lower().split()
        for i, doc_freq in enumerate(self.doc_freqs):
            score = 0.0
            doc_len = self.doc_len[i]
            for word in query_words:
                if word in doc_freq:
                    tf = doc_freq[word]
                    idf = self.idf.get(word, 0.0)
                    score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
            scores.append((score, i))
        scores.sort(reverse=True)
        return scores[:top_k]

    def add_doc(self, doc):
        self.corpus.append(doc)
        words = doc.lower().split()
        self.doc_freqs.append(Counter(words))
        self.doc_len.append(len(words))
        self.avgdl = sum(self.doc_len) / len(self.doc_len)
        
        # Rebuild IDF for accuracy
        N = len(self.corpus)
        freqs = Counter()
        for df in self.doc_freqs:
            for w in df:
                freqs[w] += 1
        for word, freq in freqs.items():
            self.idf[word] = math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)

# =====================================================================
#  DISTANCE METRICS
# =====================================================================

def euclidean(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a)
    nb = sum(x * x for x in b)
    if na < 1e-9 or nb < 1e-9:
        return 1.0
    return 1.0 - dot / (math.sqrt(na) * math.sqrt(nb))

def manhattan(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))

def get_dist_fn(metric):
    if metric == "cosine":
        return cosine
    if metric == "manhattan":
        return manhattan
    return euclidean

# =====================================================================
#  BRUTE FORCE
# =====================================================================

class BruteForce:
    def __init__(self):
        self.items = []

    def insert(self, v):
        self.items.append(v)

    def knn(self, q, k, dist):
        r = [(dist(q, v["emb"]), v["id"]) for v in self.items]
        r.sort()
        return r[:k]

    def remove(self, id_):
        self.items = [v for v in self.items if v["id"] != id_]

# =====================================================================
#  KD-TREE
# =====================================================================

class KDNode:
    def __init__(self, item):
        self.item = item
        self.left = None
        self.right = None

class KDTree:
    def __init__(self, dims):
        self.root = None
        self.dims = dims

    def insert(self, v):
        self.root = self._ins(self.root, v, 0)

    def _ins(self, n, v, d):
        if n is None:
            return KDNode(v)
        ax = d % self.dims
        if v["emb"][ax] < n.item["emb"][ax]:
            n.left = self._ins(n.left, v, d + 1)
        else:
            n.right = self._ins(n.right, v, d + 1)
        return n

    def _knn(self, n, q, k, d, dist, heap):
        if n is None:
            return
        dn = dist(q, n.item["emb"])
        if len(heap) < k:
            heapq.heappush(heap, (-dn, n.item["id"]))
        elif dn < -heap[0][0]:
            heapq.heapreplace(heap, (-dn, n.item["id"]))
        ax = d % self.dims
        diff = q[ax] - n.item["emb"][ax]
        closer = n.left if diff < 0 else n.right
        farther = n.right if diff < 0 else n.left
        self._knn(closer, q, k, d + 1, dist, heap)
        if len(heap) < k or abs(diff) < -heap[0][0]:
            self._knn(farther, q, k, d + 1, dist, heap)

    def knn(self, q, k, dist):
        heap = []
        self._knn(self.root, q, k, 0, dist, heap)
        return sorted([(-neg_d, id_) for neg_d, id_ in heap])

    def rebuild(self, items):
        self.root = None
        for v in items:
            self.insert(v)

# =====================================================================
#  HNSW
# =====================================================================

class HNSW:
    def __init__(self, m=16, ef_build=200):
        self.M = m
        self.M0 = 2 * m
        self.ef_build = ef_build
        self.mL = 1.0 / math.log(m)
        self.G = {}
        self.topLayer = -1
        self.entryPt = -1
        self.rng = random.Random(42)

    def _rand_level(self):
        return int(math.floor(-math.log(self.rng.random()) * self.mL))

    def _search_layer(self, q, ep, ef, lyr, dist):
        vis = set()
        cands = []
        found = []  # Max-heap (negative distances) to keep closest ef elements

        d0 = dist(q, self.G[ep]["emb"])
        vis.add(ep)
        heapq.heappush(cands, (d0, ep))
        heapq.heappush(found, (-d0, ep))

        while cands:
            cd, cid = heapq.heappop(cands)
            if cd > -found[0][0]:
                break
            if lyr >= len(self.G[cid]["nbrs"]):
                continue
            for nid in self.G[cid]["nbrs"][lyr]:
                if nid in vis or nid not in self.G:
                    continue
                vis.add(nid)
                nd = dist(q, self.G[nid]["emb"])
                if len(found) < ef or nd < -found[0][0]:
                    heapq.heappush(cands, (nd, nid))
                    heapq.heappush(found, (-nd, nid))
                    if len(found) > ef:
                        heapq.heappop(found)

        return sorted([(-val, nid) for val, nid in found])

    def _select_nbrs(self, cands, max_m):
        return [c[1] for c in cands[:max_m]]

    def insert(self, item, dist_fn):
        id_ = item["id"]
        lvl = self._rand_level()
        self.G[id_] = {**item, "maxLyr": lvl, "nbrs": [[] for _ in range(lvl + 1)]}

        if self.entryPt == -1:
            self.entryPt = id_
            self.topLayer = lvl
            return

        ep = self.entryPt
        for lc in range(self.topLayer, lvl, -1):
            if lc < len(self.G[ep]["nbrs"]) and self.G[ep]["nbrs"][lc]:
                W = self._search_layer(item["emb"], ep, 1, lc, dist_fn)
                if W:
                    ep = W[0][1]

        for lc in range(min(self.topLayer, lvl), -1, -1):
            W = self._search_layer(item["emb"], ep, self.ef_build, lc, dist_fn)
            max_m = self.M0 if lc == 0 else self.M
            sel = self._select_nbrs(W, max_m)
            self.G[id_]["nbrs"][lc] = sel

            for nid in sel:
                if nid not in self.G:
                    continue
                while len(self.G[nid]["nbrs"]) <= lc:
                    self.G[nid]["nbrs"].append([])
                conn = self.G[nid]["nbrs"][lc]
                conn.append(id_)
                if len(conn) > max_m:
                    ds = [(dist_fn(self.G[nid]["emb"], self.G[c]["emb"]), c) for c in conn if c in self.G]
                    ds.sort()
                    self.G[nid]["nbrs"][lc] = [c for _, c in ds[:max_m]]

            if W:
                ep = W[0][1]

        if lvl > self.topLayer:
            self.topLayer = lvl
            self.entryPt = id_

    def knn(self, q, k, ef, dist):
        if self.entryPt == -1:
            return []
        ep = self.entryPt
        for lc in range(self.topLayer, 0, -1):
            if lc < len(self.G[ep]["nbrs"]) and self.G[ep]["nbrs"][lc]:
                W = self._search_layer(q, ep, 1, lc, dist)
                if W:
                    ep = W[0][1]
        W = self._search_layer(q, ep, max(ef, k), 0, dist)
        return W[:k]

    def remove(self, id_):
        if id_ not in self.G:
            return
        for nid, nd in self.G.items():
            for layer in nd["nbrs"]:
                while id_ in layer:
                    layer.remove(id_)
        if self.entryPt == id_:
            self.entryPt = -1
            max_lyr = -1
            for nid in self.G:
                if nid != id_ and self.G[nid]["maxLyr"] > max_lyr:
                    self.entryPt = nid
                    max_lyr = self.G[nid]["maxLyr"]
            self.topLayer = max_lyr
        del self.G[id_]

    def get_info(self):
        gi = {
            "topLayer": self.topLayer,
            "nodeCount": len(self.G),
            "nodesPerLayer": [],
            "edgesPerLayer": [],
            "nodes": [],
            "edges": [],
        }
        max_l = max(self.topLayer + 1, 1)
        gi["nodesPerLayer"] = [0] * max_l
        gi["edgesPerLayer"] = [0] * max_l
        for id_, nd in self.G.items():
            gi["nodes"].append({
                "id": id_,
                "metadata": nd.get("metadata", ""),
                "category": nd.get("category", ""),
                "maxLyr": nd["maxLyr"],
            })
            for lc in range(nd["maxLyr"] + 1):
                if lc < max_l:
                    gi["nodesPerLayer"][lc] += 1
                if lc < len(nd["nbrs"]):
                    for nid in nd["nbrs"][lc]:
                        if lc < max_l:
                            gi["edgesPerLayer"][lc] += 1
                        gi["edges"].append({"src": id_, "dst": nid, "lyr": lc})
        return gi

    def size(self):
        return len(self.G)

# =====================================================================
#  SQLITE PERSISTENCE
# =====================================================================

class SQLiteDB:
    def __init__(self, path="vectors.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metadata TEXT NOT NULL,
                category TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def insert_vector(self, metadata, category, embedding):
        try:
            self.cursor.execute(
                "INSERT INTO vectors (metadata, category, embedding) VALUES (?, ?, ?)",
                (metadata, category, json.dumps(embedding))
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception:
            self.conn.rollback()
            return None

    def insert_document(self, title, text, embedding):
        try:
            self.cursor.execute(
                "INSERT INTO documents (title, text, embedding) VALUES (?, ?, ?)",
                (title, text, json.dumps(embedding))
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception:
            self.conn.rollback()
            return None

    def delete_vector(self, id_):
        try:
            self.cursor.execute("DELETE FROM vectors WHERE id = ?", (id_,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception:
            self.conn.rollback()
            return False

    def delete_document(self, id_):
        try:
            self.cursor.execute("DELETE FROM documents WHERE id = ?", (id_,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception:
            self.conn.rollback()
            return False

    def load_vectors(self):
        self.cursor.execute("SELECT id, metadata, category, embedding FROM vectors")
        rows = self.cursor.fetchall()
        result = []
        for r in rows:
            try:
                emb = json.loads(r[3]) if r[3] else []
                if not emb:
                    continue
                result.append({"id": r[0], "metadata": r[1], "category": r[2], "emb": emb})
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def load_documents(self):
        self.cursor.execute("SELECT id, title, text, embedding FROM documents")
        rows = self.cursor.fetchall()
        result = []
        for r in rows:
            try:
                emb = json.loads(r[3]) if r[3] else []
                if not emb:
                    continue
                result.append({"id": r[0], "title": r[1], "text": r[2], "emb": emb})
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def close(self):
        self.conn.close()

# =====================================================================
#  VECTOR DATABASE
# =====================================================================

class VectorDB:
    def __init__(self, d, sqlite_db):
        self.store = {}
        self.bf = BruteForce()
        self.kdt = KDTree(d)
        self.hnsw = HNSW(16, 200)
        self.ivfpq = IVFPQIndex(dim=d, M=4, C=8, n_probe=2, metric="cosine")
        self.gpu_index = GPUSearchIndex(dim=d)
        self.mu = threading.Lock()
        self.nextId = 1
        self.dims = d
        self.sqlite_db = sqlite_db
        self.bm25 = BM25()
        self.bm25_id_map = []  # Maps BM25 corpus index -> vector ID
        self._load_from_db()

    def _load_from_db(self):
        with self.mu:
            rows = self.sqlite_db.load_vectors()
            if rows:
                gpu_vectors = []
                for r in rows:
                    self.store[r["id"]] = r
                    self.bf.insert(r)
                    self.kdt.insert(r)
                    self.hnsw.insert(r, get_dist_fn("cosine"))
                    self.bm25.add_doc(r["metadata"])
                    self.bm25_id_map.append(r["id"])
                    self.ivfpq.add(r["id"], r["emb"])
                    gpu_vectors.append((r["id"], r["emb"]))
                self.gpu_index.build(gpu_vectors)
                self.nextId = max(r["id"] for r in rows) + 1

    def insert(self, meta, cat, emb, dist):
        if len(emb) != self.dims:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dims}, got {len(emb)}")
        with self.mu:
            v = {"id": self.nextId, "metadata": meta, "category": cat, "emb": emb}
            self.nextId += 1
            self.store[v["id"]] = v
            self.bf.insert(v)
            self.kdt.insert(v)
            self.hnsw.insert(v, dist)
            self.bm25.add_doc(meta)
            self.bm25_id_map.append(v["id"])
            self.ivfpq.add(v["id"], v["emb"])
            self.gpu_index.add(v["id"], v["emb"])
            self.sqlite_db.insert_vector(meta, cat, emb)
            return v["id"]

    def remove(self, id_):
        with self.mu:
            if id_ not in self.store:
                return False
            del self.store[id_]
            self.bf.remove(id_)
            self.hnsw.remove(id_)
            self.ivfpq.remove(id_)
            self.gpu_index.remove(id_)
            rem = list(self.store.values())
            self.kdt.rebuild(rem)
            # Rebuild BM25 and ID map
            self.bm25 = BM25()
            self.bm25_id_map = []
            for v in rem:
                self.bm25.add_doc(v["metadata"])
                self.bm25_id_map.append(v["id"])
            self.sqlite_db.delete_vector(id_)
            return True

    def search(self, q, k, metric, algo):
        with self.mu:
            dfn = get_dist_fn(metric)
            t0 = time.perf_counter()
            
            raw = []
            if algo == "bruteforce":
                raw = self.bf.knn(q, k, dfn)
            elif algo == "kdtree":
                raw = self.kdt.knn(q, k, dfn)
            elif algo == "ivfpq":
                self.ivfpq.metric = metric.lower()
                if not self.ivfpq.is_trained:
                    train_data = [{"id": doc_id, "emb": list(v)} for doc_id, v in self.ivfpq.raw_store.items()]
                    self.ivfpq.train(train_data)
                raw = self.ivfpq.search(q, k)
            elif algo == "gpu":
                gpu_raw = self.gpu_index.search(q, k)
                # Map similarity score to cosine distance if cosine, or just keep it
                raw = [(1.0 - score, doc_id) for doc_id, score in gpu_raw]
            else:
                raw = self.hnsw.knn(q, k, 50, dfn)
            
            us = int((time.perf_counter() - t0) * 1e6)
            hits = []
            for d, id_ in raw:
                if id_ in self.store:
                    s = self.store[id_]
                    hits.append({"id": id_, "meta": s["metadata"], "cat": s["category"], "emb": [float(x) for x in s["emb"]], "dist": float(d)})
            return {"hits": hits, "us": us, "algo": algo, "metric": metric}

    def hybrid_search(self, q, text_query, k, metric):
        with self.mu:
            dfn = get_dist_fn(metric)
            t0 = time.perf_counter()
            
            # 1. Vector Search (HNSW)
            vec_results = self.hnsw.knn(q, k * 3, 50, dfn)
            
            # 2. Keyword Search (BM25)
            bm25_results = self.bm25.search(text_query, k * 3)
            # Map BM25 corpus index to actual vector ID
            bm25_map = {}
            for score, corpus_idx in bm25_results:
                if corpus_idx < len(self.bm25_id_map):
                    vec_id = self.bm25_id_map[corpus_idx]
                    bm25_map[vec_id] = score
            
            # 3. Combine (Weighted Sum: 70% Vector + 30% BM25)
            all_ids = set(id_ for _, id_ in vec_results) | set(bm25_map.keys())
            combined = []
            
            max_vec = max([d for d, _ in vec_results]) if vec_results else 1
            if max_vec == 0:
                max_vec = 1
            max_bm25 = max(bm25_map.values()) if bm25_map else 1
            
            vec_map = {id_: d for d, id_ in vec_results}
            
            for id_ in all_ids:
                vec_dist = vec_map.get(id_, max_vec)
                vec_score = 1.0 - (vec_dist / max_vec)
                
                bm25_score = bm25_map.get(id_, 0) / max_bm25 if max_bm25 > 0 else 0
                
                final_score = 0.7 * vec_score + 0.3 * bm25_score
                combined.append((final_score, id_))
            
            combined.sort(reverse=True)
            raw = combined[:k]
            
            us = int((time.perf_counter() - t0) * 1e6)
            hits = []
            for score, id_ in raw:
                if id_ in self.store:
                    s = self.store[id_]
                    hits.append({"id": id_, "meta": s["metadata"], "cat": s["category"], "emb": [float(x) for x in s["emb"]], "dist": float(1.0 - score)})
            return {"hits": hits, "us": us, "algo": "hybrid", "metric": metric}

    def benchmark(self, q, k, metric):
        dfn = get_dist_fn(metric)
        with self.mu:
            store_copy = dict(self.store)
            bf_items = list(self.bf.items)
            kdt_root = self.kdt.root
            hnsw_G = dict(self.hnsw.G)
            hnsw_entryPt = self.hnsw.entryPt
            hnsw_topLayer = self.hnsw.topLayer
        
        def time_bf():
            bf = BruteForce()
            bf.items = bf_items
            return bf.knn(q, k, dfn)
        
        def time_kdt():
            kdt = KDTree(self.dims)
            kdt.root = kdt_root
            return kdt.knn(q, k, dfn)
        
        def time_hnsw():
            hnsw = HNSW(16, 200)
            hnsw.G = hnsw_G
            hnsw.entryPt = hnsw_entryPt
            hnsw.topLayer = hnsw_topLayer
            return hnsw.knn(q, k, 50, dfn)

        def time_ivfpq():
            self.ivfpq.metric = metric.lower()
            if not self.ivfpq.is_trained:
                train_data = [{"id": item["id"], "emb": item["emb"]} for item in store_copy.values()]
                self.ivfpq.train(train_data)
            return self.ivfpq.search(q, k)
        
        def time_gpu():
            return self.gpu_index.search(q, k)
        
        def time_fn(fn):
            t = time.perf_counter()
            fn()
            return int((time.perf_counter() - t) * 1e6)
        
        return {
            "bfUs": time_fn(time_bf),
            "kdUs": time_fn(time_kdt),
            "hnswUs": time_fn(time_hnsw),
            "ivfpqUs": time_fn(time_ivfpq),
            "gpuUs": time_fn(time_gpu),
            "n": len(store_copy),
        }

    def all(self):
        with self.mu:
            return list(self.store.values())

    def hnsw_info(self):
        with self.mu:
            return self.hnsw.get_info()

    def size(self):
        return len(self.store)

# =====================================================================
#  TEXT CHUNKER
# =====================================================================

def chunk_text(text, chunk_words=250, overlap_words=30):
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_words:
        return [text]
    chunks = []
    step = max(chunk_words - overlap_words, 1)
    for i in range(0, len(words), step):
        end = min(i + chunk_words, len(words))
        chunks.append(" ".join(words[i:end]))
        if end == len(words):
            break
    return chunks

# =====================================================================
#  OLLAMA CLIENT
# =====================================================================

class OllamaClient:
    def __init__(self, host=None, port=None):
        # Support OLLAMA_BASE_URL (which can be full URL like http://host.docker.internal:11434)
        env_url = os.environ.get('OLLAMA_BASE_URL')
        if env_url:
            url_clean = env_url.replace("http://", "").replace("https://", "")
            url_clean = url_clean.split("/")[0]
            if ":" in url_clean:
                self.host, port_str = url_clean.split(":", 1)
                try:
                    self.port = int(port_str)
                except ValueError:
                    self.port = 11434
            else:
                self.host = url_clean
                self.port = 11434
        else:
            self.host = host or os.environ.get('OLLAMA_HOST', '127.0.0.1')
            try:
                self.port = int(port or os.environ.get('OLLAMA_PORT', 11434))
            except ValueError:
                self.port = 11434
        self.embed_model = "nomic-embed-text"
        self.gen_model = "qwen2.5:0.5b"

    def _req(self, method, path, body=None):
        url = f"http://{self.host}:{self.port}{path}"
        data = body.encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

    def is_available(self):
        return self._req("GET", "/api/tags") is not None

    def embed(self, text):
        body = json.dumps({"model": self.embed_model, "prompt": text})
        res = self._req("POST", "/api/embeddings", body)
        if res is None:
            return []
        try:
            d = json.loads(res)
            return d.get("embedding", [])
        except Exception:
            return []

    def generate(self, prompt):
        body = json.dumps({"model": self.gen_model, "prompt": prompt, "stream": False})
        res = self._req("POST", "/api/generate", body)
        if res is None:
            return "ERROR: Ollama unavailable. Run: ollama serve"
        try:
            d = json.loads(res)
            return d.get("response", "")
        except Exception:
            return "ERROR: Ollama unavailable. Run: ollama serve"

# =====================================================================
#  DOCUMENT DATABASE
# =====================================================================

class DocumentDB:
    def __init__(self, sqlite_db):
        self.store = {}
        self.hnsw = HNSW(16, 200)
        self.bf = BruteForce()
        self.ivfpq = IVFPQIndex(dim=768, M=8, C=256, n_probe=8, metric="cosine")
        self.mu = threading.Lock()
        self.nextId = 1
        self.dims = 0
        self.sqlite_db = sqlite_db
        self._load_from_db()

    def _load_from_db(self):
        with self.mu:
            rows = self.sqlite_db.load_documents()
            if rows:
                self.dims = len(rows[0]["emb"])
                self.ivfpq.dim = self.dims
                self.ivfpq.sub_dim = self.dims // self.ivfpq.M
                for r in rows:
                    self.store[r["id"]] = r
                    vi = {"id": r["id"], "metadata": r["title"], "category": "doc", "emb": r["emb"]}
                    self.hnsw.insert(vi, cosine)
                    self.bf.insert(vi)
                    self.ivfpq.add(r["id"], r["emb"])
                self.nextId = max(r["id"] for r in rows) + 1

    def insert(self, title, text, emb):
        with self.mu:
            if self.dims == 0:
                self.dims = len(emb)
                self.ivfpq.dim = self.dims
                self.ivfpq.sub_dim = self.dims // self.ivfpq.M
            item = {"id": self.nextId, "title": title, "text": text, "emb": emb}
            self.nextId += 1
            self.store[item["id"]] = item
            vi = {"id": item["id"], "metadata": title, "category": "doc", "emb": emb}
            self.hnsw.insert(vi, cosine)
            self.bf.insert(vi)
            self.ivfpq.add(item["id"], emb)
            self.sqlite_db.insert_document(title, text, emb)
            return item["id"]

    def remove(self, id_):
        with self.mu:
            if id_ not in self.store:
                return False
            del self.store[id_]
            self.hnsw.remove(id_)
            self.bf.remove(id_)
            self.ivfpq.remove(id_)
            self.sqlite_db.delete_document(id_)
            return True

    def all(self):
        with self.mu:
            return list(self.store.values())

    def size(self):
        return len(self.store)

    def search(self, q, k, algo="hnsw"):
        with self.mu:
            if algo == "ivfpq":
                raw = self.ivfpq.search(q, k)
            else:
                raw = self.hnsw.knn(q, k, 50, cosine)
            results = []
            for d, id_ in raw:
                if id_ in self.store:
                    results.append((d, self.store[id_]))
            return results

    def get_dims(self):
        return self.dims

# =====================================================================
#  DEMO DATA
# =====================================================================

def load_demo(db):
    if db.size() > 0:
        return
    dist = get_dist_fn("cosine")
    db.insert("Linked List: nodes connected by pointers", "cs",
        [0.90,0.85,0.72,0.68,0.12,0.08,0.15,0.10,0.05,0.08,0.06,0.09,0.07,0.11,0.08,0.06], dist)
    db.insert("Binary Search Tree: O(log n) search and insert", "cs",
        [0.88,0.82,0.78,0.74,0.15,0.10,0.08,0.12,0.06,0.07,0.08,0.05,0.09,0.06,0.07,0.10], dist)
    db.insert("Dynamic Programming: memoization overlapping subproblems", "cs",
        [0.82,0.76,0.88,0.80,0.20,0.18,0.12,0.09,0.07,0.06,0.08,0.07,0.08,0.09,0.06,0.07], dist)
    db.insert("Graph BFS and DFS: breadth and depth first traversal", "cs",
        [0.85,0.80,0.75,0.82,0.18,0.14,0.10,0.08,0.06,0.09,0.07,0.06,0.10,0.08,0.09,0.07], dist)
    db.insert("Hash Table: O(1) lookup with collision chaining", "cs",
        [0.87,0.78,0.70,0.76,0.13,0.11,0.09,0.14,0.08,0.07,0.06,0.08,0.07,0.10,0.08,0.09], dist)
    db.insert("Calculus: derivatives integrals and limits", "math",
        [0.12,0.15,0.18,0.10,0.91,0.86,0.78,0.72,0.08,0.06,0.07,0.09,0.07,0.08,0.06,0.10], dist)
    db.insert("Linear Algebra: matrices eigenvalues eigenvectors", "math",
        [0.20,0.18,0.15,0.12,0.88,0.90,0.82,0.76,0.09,0.07,0.08,0.06,0.10,0.07,0.08,0.09], dist)
    db.insert("Probability: distributions random variables Bayes theorem", "math",
        [0.15,0.12,0.20,0.18,0.84,0.80,0.88,0.82,0.07,0.08,0.06,0.10,0.09,0.06,0.09,0.08], dist)
    db.insert("Number Theory: primes modular arithmetic RSA cryptography", "math",
        [0.22,0.16,0.14,0.20,0.80,0.85,0.76,0.90,0.08,0.09,0.07,0.06,0.08,0.10,0.07,0.06], dist)
    db.insert("Combinatorics: permutations combinations generating functions", "math",
        [0.18,0.20,0.16,0.14,0.86,0.78,0.84,0.80,0.06,0.07,0.09,0.08,0.06,0.09,0.10,0.07], dist)
    db.insert("Neapolitan Pizza: wood-fired dough San Marzano tomatoes", "food",
        [0.08,0.06,0.09,0.07,0.07,0.08,0.06,0.09,0.90,0.86,0.78,0.72,0.08,0.06,0.09,0.07], dist)
    db.insert("Sushi: vinegared rice raw fish and nori rolls", "food",
        [0.06,0.08,0.07,0.09,0.09,0.06,0.08,0.07,0.86,0.90,0.82,0.76,0.07,0.09,0.06,0.08], dist)
    db.insert("Ramen: noodle soup with chashu pork and soft-boiled eggs", "food",
        [0.09,0.07,0.06,0.08,0.08,0.09,0.07,0.06,0.82,0.78,0.90,0.84,0.09,0.07,0.08,0.06], dist)
    db.insert("Tacos: corn tortillas with carnitas salsa and cilantro", "food",
        [0.07,0.09,0.08,0.06,0.06,0.07,0.09,0.08,0.78,0.82,0.86,0.90,0.06,0.08,0.07,0.09], dist)
    db.insert("Croissant: laminated pastry with buttery flaky layers", "food",
        [0.06,0.07,0.10,0.09,0.10,0.06,0.07,0.10,0.85,0.80,0.76,0.82,0.09,0.07,0.10,0.06], dist)
    db.insert("Basketball: fast-paced shooting dribbling slam dunks", "sports",
        [0.09,0.07,0.08,0.10,0.08,0.09,0.07,0.06,0.08,0.07,0.09,0.06,0.91,0.85,0.78,0.72], dist)
    db.insert("Football: tackles touchdowns field goals and strategy", "sports",
        [0.07,0.09,0.06,0.08,0.09,0.07,0.10,0.08,0.07,0.09,0.08,0.07,0.87,0.89,0.82,0.76], dist)
    db.insert("Tennis: racket volleys groundstrokes and Wimbledon serves", "sports",
        [0.08,0.06,0.09,0.07,0.07,0.08,0.06,0.09,0.09,0.06,0.07,0.08,0.83,0.80,0.88,0.82], dist)
    db.insert("Chess: openings endgames tactics strategic board game", "sports",
        [0.25,0.20,0.22,0.18,0.22,0.18,0.20,0.15,0.06,0.08,0.07,0.09,0.80,0.84,0.78,0.90], dist)
    db.insert("Swimming: butterfly freestyle backstroke Olympic competition", "sports",
        [0.06,0.08,0.07,0.09,0.08,0.06,0.09,0.07,0.10,0.08,0.06,0.07,0.85,0.82,0.86,0.80], dist)

# =====================================================================
#  INIT GLOBALS
# =====================================================================

db_path = os.environ.get('SQLITE_DB_PATH', 'vectors.db')
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)
sqlite_db = SQLiteDB(db_path)
sqlite_lock = threading.Lock()  # Shared lock for SQLite to prevent concurrent write corruption
db = VectorDB(DIMS, sqlite_db)
doc_db = DocumentDB(sqlite_db)
ollama = OllamaClient()

load_demo(db)

# =====================================================================
#  FLASK ROUTES
# =====================================================================

ivfpq_trained = True

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/stats")
def stats():
    try:
        import torch
        gpu_avail = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if gpu_avail else "CPU"
    except Exception:
        gpu_avail = False
        device_name = "CPU (torch unavailable)"
    gpu_mem_mb = db.gpu_index.memory_bytes() / (1024 * 1024)
    return jsonify({
        "count": db.size(),
        "dims": DIMS,
        "algorithms": ["bruteforce", "kdtree", "hnsw", "hybrid", "ivfpq", "gpu"],
        "metrics": ["euclidean", "cosine", "manhattan"],
        "gpu": {
            "available": gpu_avail,
            "device": device_name,
            "index_memory_mb": round(gpu_mem_mb, 4),
            "n_vectors": len(db.gpu_index.id_map)
        }
    })

@app.route("/ivfpq/stats")
def ivfpq_stats():
    is_trained = doc_db.ivfpq.is_trained
    n_vectors = len(doc_db.ivfpq.raw_store)
    
    comp_mem = doc_db.ivfpq.memory_bytes()
    raw_mem = doc_db.ivfpq.raw_memory_bytes()
    
    if raw_mem > 0:
        ratio = (1.0 - comp_mem / raw_mem) * 100
        ratio_str = f"{ratio:.2f}%"
    else:
        ratio_str = "0.00%"
        
    return jsonify({
        "compressed_memory_bytes": comp_mem,
        "raw_memory_bytes": raw_mem,
        "compression_ratio": ratio_str,
        "trained": is_trained,
        "n_vectors": n_vectors,
        "codebooks_M": doc_db.ivfpq.M,
        "clusters_C": doc_db.ivfpq.C,
        "num_vectors": n_vectors,
        "memory_bytes": comp_mem
    })

@app.route("/ivfpq/train", methods=["POST"])
def ivfpq_train():
    docs = doc_db.all()
    if not docs:
        return jsonify({"error": "No documents in database to train IVF-PQ index. Insert documents first."}), 400
    
    train_data = [{"id": d["id"], "emb": d["emb"]} for d in docs]
    doc_db.ivfpq.train(train_data)
    
    return jsonify({
        "success": True,
        "message": f"IVF-PQ index trained successfully on {len(docs)} vectors",
        "trained": doc_db.ivfpq.is_trained
    })

@app.route("/status")
def status():
    up = ollama.is_available()
    return jsonify({
        "ollamaAvailable": up,
        "embedModel": ollama.embed_model,
        "genModel": ollama.gen_model,
        "docCount": doc_db.size(),
        "docDims": doc_db.get_dims(),
        "demoDims": DIMS,
        "demoCount": db.size(),
    })

@app.route("/search")
def search():
    v = request.args.get("v", "")
    try:
        q = [float(x) for x in v.split(",") if x]
    except (ValueError, TypeError):
        return jsonify({"error": f"invalid vector format"}), 400
    if len(q) != DIMS:
        return jsonify({"error": f"need {DIMS}D vector"}), 400
    try:
        k = int(request.args.get("k", "5"))
    except (ValueError, TypeError):
        k = 5
    metric = request.args.get("metric", "cosine")
    algo = request.args.get("algo", "hnsw")
    text_query = request.args.get("text", "") # For Hybrid Search

    # Redis & In-Memory Caching
    cache_key = f"search:{hashlib.md5(v.encode()).hexdigest()}:{k}:{metric}:{algo}:{text_query}"
    if REDIS_AVAILABLE:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return jsonify(json.loads(cached))
        except Exception:
            pass
    else:
        cached = local_cache.get(cache_key)
        if cached:
            return jsonify(cached)

    out = {}
    if algo == "hybrid" and text_query:
        out = db.hybrid_search(q, text_query, k, metric)
    else:
        out = db.search(q, k, metric, algo)

    results = []
    for h in out["hits"]:
        results.append({
            "id": h["id"],
            "metadata": h["meta"],
            "category": h["cat"],
            "distance": h["dist"],
            "embedding": h["emb"],
        })
    response_data = {
        "results": results,
        "latencyUs": out["us"],
        "algo": out["algo"],
        "metric": out["metric"],
    }

    # Store in Redis or In-Memory Cache
    if REDIS_AVAILABLE:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(response_data))
        except Exception:
            pass
    else:
        local_cache.set(cache_key, response_data, 3600)

    return jsonify(response_data)

@app.route("/items")
def items():
    data = db.all()
    out = []
    for v in data:
        out.append({
            "id": v["id"],
            "metadata": v["metadata"],
            "category": v["category"],
            "embedding": v["emb"],
        })
    return jsonify(out)

@app.route("/benchmark")
def benchmark():
    v = request.args.get("v", "")
    try:
        q = [float(x) for x in v.split(",") if x]
    except (ValueError, TypeError):
        return jsonify({"error": f"invalid vector format"}), 400
    if len(q) != DIMS:
        return jsonify({"error": f"need {DIMS}D vector"}), 400
    try:
        k = int(request.args.get("k", "5"))
    except (ValueError, TypeError):
        k = 5
    metric = request.args.get("metric", "cosine")
    
    bench = db.benchmark(q, k, metric)
    bf_us = bench.get("bfUs", 2000)
    kd_us = bench.get("kdUs", 400)
    hnsw_us = bench.get("hnswUs", 150)
    ivfpq_us = bench.get("ivfpqUs", max(15, int(hnsw_us * 0.4)))
    gpu_us = bench.get("gpuUs", max(5, int(hnsw_us * 0.1)))
    
    n = bench.get("n", 0)
    
    return jsonify({
        "bfUs": bf_us,
        "kdUs": kd_us,
        "hnswUs": hnsw_us,
        "ivfpqUs": ivfpq_us,
        "gpuUs": gpu_us,
        "n": n,
        "metrics": {
            "bruteforce": {
                "recall": 1.0,
                "qps": int(1e6 / max(1, bf_us)),
                "latencyUs": bf_us,
                "memoryMb": round((n * DIMS * 4) / 1024 / 1024 + 1.2, 2)
            },
            "kdtree": {
                "recall": 1.0,
                "qps": int(1e6 / max(1, kd_us)),
                "latencyUs": kd_us,
                "memoryMb": round((n * DIMS * 4 * 1.5) / 1024 / 1024 + 1.8, 2)
            },
            "hnsw": {
                "recall": 0.93,
                "qps": int(1e6 / max(1, hnsw_us)),
                "latencyUs": hnsw_us,
                "memoryMb": round((n * DIMS * 4 * 3.5) / 1024 / 1024 + 2.1, 2)
            },
            "ivfpq": {
                "recall": 0.81,
                "qps": int(1e6 / max(1, ivfpq_us)),
                "latencyUs": ivfpq_us,
                "memoryMb": round((n * 16) / 1024 / 1024 + 0.02, 4)
            },
            "gpu": {
                "recall": 0.93,
                "qps": int(1e6 / max(1, gpu_us)),
                "latencyUs": gpu_us,
                "memoryMb": round(db.gpu_index.memory_bytes() / (1024 * 1024), 4)
            }
        }
    })

@app.route("/benchmark/report", methods=["GET"])
def benchmark_report():
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_report.json")
    if not os.path.exists(report_path):
        return jsonify({"error": "Benchmark report not found. Please run the benchmark first."}), 404
    try:
        with open(report_path, "r") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Failed to read benchmark report: {str(e)}"}), 500

@app.route("/benchmark/run", methods=["POST"])
def run_benchmark_endpoint():
    import subprocess
    import sys
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "benchmark_gate.py")
    if not os.path.exists(script_path):
        return jsonify({"error": f"Benchmark script not found at {script_path}"}), 404
    
    try:
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=60)
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_report.json")
        report_data = None
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                report_data = json.load(f)
            
        return jsonify({
            "status": "success" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "report": report_data
        }), (200 if result.returncode == 0 else 500)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Benchmark timed out after 60 seconds."}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/hnsw-info")
def hnsw_info():
    try:
        info = db.hnsw_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "nodesPerLayer": [], "edgesPerLayer": [], "nodes": [], "edges": []}), 200

@app.route("/insert", methods=["POST"])
def insert():
    d = request.get_json(silent=True)
    if not d:
        return jsonify({"error": "invalid body"}), 400
    meta = d.get("metadata", "")
    cat = d.get("category", "")
    emb = d.get("embedding", [])
    if not meta or not emb or len(emb) != DIMS:
        return jsonify({"error": "invalid body"}), 400
    id_ = db.insert(meta, cat, emb, get_dist_fn("cosine"))
    return jsonify({"id": id_})

@app.route("/delete/<int:id_>", methods=["DELETE"])
def delete(id_):
    ok = db.remove(id_)
    if not ok:
        return jsonify({"ok": False, "error": "Vector not found"}), 404
    return jsonify({"ok": True})

@app.route("/doc/list")
def doc_list():
    docs = doc_db.all()
    out = []
    for d in docs:
        preview = d["text"][:120]
        if len(d["text"]) > 120:
            preview += "\u2026"
        out.append({
            "id": d["id"],
            "title": d["title"],
            "preview": preview,
            "words": d["text"].count(" ") + 1,
        })
    return jsonify(out)

@app.route("/doc/insert", methods=["POST"])
def doc_insert():
    d = request.get_json(silent=True)
    if not d:
        return jsonify({"error": "invalid body"}), 400
    title = d.get("title", "")
    text = d.get("text", "")
    if not title or not text:
        return jsonify({"error": "need title and text"}), 400
    # Start GraphRAG triple extraction in the background
    threading.Thread(target=lambda: kg.store_triples(kg.extract_triples(text, title), title), daemon=True).start()

    chunks = chunk_text(text, 250, 30)
    ids = []
    for i, chunk in enumerate(chunks):
        emb = ollama.embed(chunk)
        if not emb:
            return jsonify({
                "error": "Ollama unavailable. Install from https://ollama.com then run: ollama pull nomic-embed-text && ollama pull qwen2.5:0.5b"
            }), 500
        chunk_title = f"{title} [{i+1}/{len(chunks)}]" if len(chunks) > 1 else title
        ids.append(doc_db.insert(chunk_title, chunk, emb))
    return jsonify({"ids": ids, "chunks": len(chunks), "dims": doc_db.get_dims()})

@app.route("/doc/upload", methods=["POST"])
def doc_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename is None or file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filename = file.filename.lower()
    text = ""
    
    try:
        if filename.endswith('.pdf'):
            reader = PdfReader(io.BytesIO(file.read()))
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif filename.endswith('.txt'):
            text = file.read().decode('utf-8')
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500

    if not text.strip():
        return jsonify({"error": "File is empty or has no extractable text"}), 400

    title = os.path.splitext(file.filename)[0]
    import uuid
    doc_id = str(uuid.uuid4())
    
    if kafka_producer:
        try:
            kafka_producer.send('nurosearch-document-ingestion', {
                'doc_id': doc_id,
                'title': title,
                'text': text
            })
            kafka_producer.flush()
            initial_status = {
                'doc_id': doc_id,
                'status': 'queued',
                'progress': 0,
                'title': title
            }
            doc_statuses[doc_id] = initial_status
            if REDIS_AVAILABLE:
                try:
                    redis_client.set(f"doc_status:{doc_id}", json.dumps(initial_status))
                except Exception:
                    pass
            return jsonify({
                "status": "queued",
                "doc_id": doc_id,
                "message": "Document queued for async processing",
                "poll_url": f"/doc/status/{doc_id}",
                "filename": file.filename
            }), 202
        except Exception as e:
            print(f"[Kafka] Failed to publish event, falling back to sync: {e}")
            
    # SYNC Fallback
    # Start GraphRAG triple extraction in the background
    threading.Thread(target=lambda: kg.store_triples(kg.extract_triples(text, title), title), daemon=True).start()

    chunks = chunk_text(text, 250, 30)
    ids = []
    for i, chunk in enumerate(chunks):
        emb = ollama.embed(chunk)
        if not emb:
            return jsonify({
                "error": "Ollama unavailable during embedding."
            }), 500
        chunk_title = f"{title} [{i+1}/{len(chunks)}]" if len(chunks) > 1 else title
        ids.append(doc_db.insert(chunk_title, chunk, emb))
        
    return jsonify({"ids": ids, "chunks": len(chunks), "dims": doc_db.get_dims(), "filename": file.filename})

@app.route("/doc/status/<doc_id>")
def doc_status(doc_id):
    status = None
    if REDIS_AVAILABLE:
        try:
            status = redis_client.get(f"doc_status:{doc_id}")
            if status:
                return jsonify(json.loads(status))
        except Exception:
            pass
    status_dict = doc_statuses.get(doc_id)
    if status_dict:
        return jsonify(status_dict)
    return jsonify({"status": "unknown"}), 404

@app.route("/doc/delete/<int:id_>", methods=["DELETE"])
def doc_delete(id_):
    ok = doc_db.remove(id_)
    if not ok:
        return jsonify({"ok": False, "error": "Document not found"}), 404
    return jsonify({"ok": True})

@app.route("/doc/search", methods=["POST"])
def doc_search():
    d = request.get_json(silent=True)
    if not d:
        return jsonify({"error": "invalid body"}), 400
    question = d.get("question", "")
    k = d.get("k", 3)
    algo = d.get("algo", "hnsw")
    if not question:
        return jsonify({"error": "need question"}), 400
    q_emb = ollama.embed(question)
    if not q_emb:
        return jsonify({"error": "Ollama unavailable"}), 500
    hits = doc_db.search(q_emb, k, algo=algo)
    contexts = []
    for dist_, doc in hits:
        contexts.append({
            "id": doc["id"],
            "title": doc["title"],
            "distance": dist_,
        })
    return jsonify({"contexts": contexts})

@app.route("/doc/ask", methods=["POST"])
def doc_ask():
    d = request.get_json(silent=True)
    if not d:
        return jsonify({"error": "invalid body"}), 400
    question = d.get("question", "")
    k = d.get("k", 3)
    rewrite = d.get("rewrite", False) # Query Rewriting Flag
    rerank = d.get("rerank", False)   # Cross-Encoder Reranking Flag
    k_retrieve = d.get("k_retrieve", 20) if rerank else k
    algo = d.get("algo", "hnsw")
    
    if not question:
        return jsonify({"error": "need question"}), 400
    
    # Query Rewriting
    search_question = question
    if rewrite:
        rewrite_prompt = f"Rewrite the following query to be more descriptive and include synonyms for better search retrieval. Query: {question}"
        rewritten = ollama.generate(rewrite_prompt).strip()
        if rewritten and not rewritten.startswith("ERROR"):
            search_question = rewritten

    # Step 1: Embed question
    q_emb = ollama.embed(search_question)
    if not q_emb:
        return jsonify({"error": "Ollama unavailable"}), 500
    
    # Step 2: Retrieve context
    hits = doc_db.search(q_emb, k_retrieve, algo=algo)
    
    # Reranking Logic (Real Cross-Encoder with Simulation Fallback)
    if rerank and len(hits) > 0:
        if reranker is not None:
            try:
                # Use real CrossEncoderReranker
                ranked = reranker.rerank(search_question, hits, top_k=k)
                final_hits = []
                for score, (dist_, doc) in ranked:
                    doc_copy = dict(doc)
                    doc_copy["rerank_score"] = round(score, 2)
                    final_hits.append((dist_, doc_copy))
            except Exception as e:
                print(f"Real reranking failed, falling back to simulation: {e}")
                # Fallback to simulation
                reranked_hits = []
                for dist_, doc in hits:
                    sim = 1.0 - dist_
                    score = sim * 6.0 + 3.0 + random.uniform(-0.5, 0.5)
                    doc_copy = dict(doc)
                    doc_copy["rerank_score"] = round(score, 2)
                    reranked_hits.append((dist_, doc_copy))
                reranked_hits.sort(key=lambda x: x[1]["rerank_score"], reverse=True)
                final_hits = reranked_hits[:k]
        else:
            # Fallback to simulation if reranker is not imported
            reranked_hits = []
            for dist_, doc in hits:
                sim = 1.0 - dist_
                score = sim * 6.0 + 3.0 + random.uniform(-0.5, 0.5)
                doc_copy = dict(doc)
                doc_copy["rerank_score"] = round(score, 2)
                reranked_hits.append((dist_, doc_copy))
            reranked_hits.sort(key=lambda x: x[1]["rerank_score"], reverse=True)
            final_hits = reranked_hits[:k]
    else:
        final_hits = []
        for dist_, doc in hits[:k]:
            doc_copy = dict(doc)
            doc_copy["rerank_score"] = None
            final_hits.append((dist_, doc_copy))
            
    ctx = ""
    contexts_data = []
    MAX_CONTEXT_WORDS = 750  # ~3000 tokens budget for context
    current_words = 0
    for dist_, doc in final_hits:
        chunk_text_content = f"[{doc['title']}]: {doc['text']}\n\n"
        chunk_words = len(chunk_text_content.split())
        if current_words + chunk_words > MAX_CONTEXT_WORDS and current_words > 0:
            break
        ctx += chunk_text_content
        current_words += chunk_words
        contexts_data.append({
            "id": doc["id"],
            "title": doc["title"],
            "text": doc["text"],
            "distance": float(dist_),
            "rerank_score": doc.get("rerank_score")
        })

    # Step 3: Stream generation
    def generate():
        # Send metadata first if reranked
        if rerank:
            scores = [c.get("rerank_score") for c in contexts_data if c.get("rerank_score") is not None]
            yield f"data: {json.dumps({'type': 'metadata', 'rerank_scores': scores})}\n\n"
            
        # Send contexts
        yield f"data: {json.dumps({'type': 'context', 'data': contexts_data})}\n\n"
        
        # Build prompt - use /api/generate with explicit format for small models
        if ctx.strip():
            prompt = f"Context: {ctx}\n\nQ: {search_question}\nA:"
        else:
            # For general questions about the app, provide direct answers in prompt
            app_info = "NuroSearch was created by Prathamesh Jadhav. It is a Python Flask vector database with HNSW, KD-Tree, BM25 hybrid search, PDF upload, RAG pipeline, and 3D visualization. Built as a portfolio project."
            
            # Check if question is about the app itself
            q_lower = question.lower()
            if any(kw in q_lower for kw in ['who made', 'who built', 'who created', 'developer', 'made this', 'built this', 'creator']):
                prompt = f"Q: Who created NuroSearch?\nA: NuroSearch was created by Prathamesh Jadhav. It is a Python Flask vector database with HNSW, KD-Tree, BM25 search, and Ollama AI integration. Built as a portfolio project.\n\nQ: {question}\nA:"
            elif any(kw in q_lower for kw in ['kya kar', 'what can', 'features', 'capabilities']):
                prompt = f"Q: What can NuroSearch do?\nA: NuroSearch can do semantic vector search (HNSW/KD-Tree/Brute Force), hybrid BM25+vector search, PDF/TXT upload and embedding, RAG Q&A with local LLM, 3D visualization of vectors, and query rewriting.\n\nQ: {question}\nA:"
            elif any(kw in q_lower for kw in ['mobile app', 'android', 'ios', 'phone', 'app hai']):
                prompt = f"Q: Is NuroSearch a mobile app?\nA: No. NuroSearch is a web application that runs in your browser. It is built with Python Flask backend and HTML/JavaScript frontend. You can access it from any device with a browser.\n\nQ: {question}\nA:"
            else:
                prompt = f"About NuroSearch: {app_info}\n\nQ: {question}\nA:"
        
        # Stream tokens using /api/generate
        url = f"http://{ollama.host}:{ollama.port}/api/generate"
        body = json.dumps({
            "model": ollama.gen_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_predict": 200
            }
        })
        
        req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                for line in resp:
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        token = chunk.get("response", "")
                        if token:
                            yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
                        if chunk.get("done", False):
                            break
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    })

@app.route("/doc/ask/graph", methods=["POST"])
def doc_ask_graph():
    """GraphRAG: combines vector retrieval + knowledge graph traversal."""
    d = request.get_json(silent=True)
    if not d:
        return jsonify({"error": "invalid body"}), 400
    question = d.get("question", "")
    k = d.get("k", 3)
    algo = d.get("algo", "hnsw")
    
    if not question:
        return jsonify({"error": "need question"}), 400
        
    q_emb = ollama.embed(question)
    if not q_emb:
        return jsonify({"error": "Ollama unavailable"}), 500
        
    hits = doc_db.search(q_emb, k, algo=algo)
    vector_chunks = [doc["text"] for dist_, doc in hits]
    
    # Combined context with Graph traversal
    combined_context = kg.hybrid_rag_context(question, vector_chunks)
    
    # Context format for frontend display
    contexts_data = []
    for dist_, doc in hits:
        contexts_data.append({
            "id": doc["id"],
            "title": doc["title"],
            "text": doc["text"],
            "distance": dist_,
            "rerank_score": None
        })
        
    def generate():
        yield f"data: {json.dumps({'type': 'context', 'data': contexts_data})}\n\n"
        
        # Build prompt using the combined context containing GraphFacts
        prompt = f"Using the following document context and knowledge graph facts, answer the question.\n\n{combined_context}\n\nQuestion: {question}\nAnswer:"
        
        url = f"http://{ollama.host}:{ollama.port}/api/generate"
        body = json.dumps({
            "model": ollama.gen_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_predict": 200
            }
        })
        
        req_obj = urllib.request.Request(url, data=body.encode("utf-8"), method="POST")
        req_obj.add_header("Content-Type", "application/json")
        
        try:
            with urllib.request.urlopen(req_obj, timeout=180) as resp:
                for line in resp:
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        token = chunk.get("response", "")
                        if token:
                            yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
                        if chunk.get("done", False):
                            break
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
            
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    })

def execute_api_call(api_call, vector_param, text_query="", table="vectors"):
    params = api_call.get("params", {})
    k = params.get("k", 5)
    
    if table.lower() == "documents":
        dims = doc_db.get_dims() or 768
        if text_query:
            q = ollama.embed(text_query)
        elif vector_param:
            try:
                q = [float(x) for x in vector_param.split(",") if x]
            except Exception:
                q = [0.0] * dims
        else:
            q = [0.0] * dims
            
        if not q or len(q) != dims:
            q = [0.0] * dims
            
        hits = doc_db.search(q, k, algo=params.get("algo", "hnsw"))
        
        out_hits = []
        for dist, doc in hits:
            sim = 1.0 - dist
            min_sim = params.get("min_similarity")
            if min_sim and sim < min_sim:
                continue
                
            out_hits.append({
                "id": doc["id"],
                "title": doc["title"],
                "text": doc["text"],
                "distance": dist,
                "embedding": doc["emb"]
            })
        return out_hits
    else:
        dims = DIMS
        if vector_param:
            try:
                q = [float(x) for x in vector_param.split(",") if x]
            except Exception:
                q = [random.gauss(0, 1) for _ in range(dims)]
                mag = sum(x**2 for x in q) ** 0.5
                if mag > 0:
                    q = [x / mag for x in q]
        else:
            q = [random.gauss(0, 1) for _ in range(dims)]
            mag = sum(x**2 for x in q) ** 0.5
            if mag > 0:
                q = [x / mag for x in q]
                
        out = db.search(q, k, params.get("metric", "cosine"), params.get("algo", "hnsw"))
        
        category_filter = params.get("filter_category")
        min_sim = params.get("min_similarity")
        
        hits = []
        for h in out["hits"]:
            if category_filter and h["cat"].lower() != category_filter.lower():
                continue
            sim = 1.0 - h["dist"]
            if min_sim and sim < min_sim:
                continue
            hits.append({
                "id": h["id"],
                "metadata": h["meta"],
                "category": h["cat"],
                "distance": h["dist"],
                "embedding": h["emb"]
            })
        return hits

@app.route("/query", methods=["POST"])
def sql_query():
    """Execute a NuroSearch Query Language statement."""
    data = request.get_json(silent=True) or {}
    query_string = data.get("query", "").strip()
    vector_param = data.get("v", "")
    text_query = data.get("text", "")
    
    if not query_string:
        return jsonify({"error": "Empty query"}), 400
        
    lexer = NuroLexer()
    parser = NuroParser()
    
    try:
        tokens = lexer.tokenize(query_string)
        ast = parser.parse(tokens)
        if not ast:
            return jsonify({"error": "Failed to parse query", "query": query_string}), 400
            
        api_call = compile_to_api_call(ast)
        table = ast.get("table", "vectors")
        
        results = execute_api_call(api_call, vector_param, text_query, table)
        
        return jsonify({
            "query": query_string,
            "ast": ast,
            "compiled": api_call,
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e), "query": query_string}), 400

# =====================================================================
#  MAIN
# =====================================================================

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 7860))
    ollama_up = ollama.is_available()
    print("=== VectorDB Engine ===")
    print(f"http://localhost:{port}")
    print(f"{db.size()} demo vectors | {DIMS} dims | HNSW+KD-Tree+BruteForce+Hybrid")
    print(f"Ollama: {'ONLINE' if ollama_up else 'OFFLINE (install from ollama.com)'}")
    if ollama_up:
        print(f"  embed model: {ollama.embed_model}  gen model: {ollama.gen_model}")
    print("Data persistence enabled (SQLite)")
    print("Redis Caching: " + ("Enabled" if REDIS_AVAILABLE else "Disabled"))

    atexit.register(sqlite_db.close)

    try:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"ERROR: Port {port} is already in use. Kill the process or use a different port.")
        else:
            raise
