ALWAYS USE :
- astro , improve-codebase-architechture,tailwind-4-docs,ui-ux-pro-max,web-design-guildelines
- (Must) ALWAYS Use DESIGN.md for this project design


# AGENT.md — NuroSearch: Complete Implementation Roadmap

> **For any AI agent or developer reading this file:**
> This document is the single source of truth for transforming NuroSearch from a strong portfolio project into a world-class, production-grade AI infrastructure system. Every feature listed here has been carefully chosen for maximum resume impact, interview talking points, and real engineering depth. Read the entire document before writing a single line of code. Each feature section tells you exactly WHAT to build, HOW to build it, WHY it matters, and WHAT jobs it unlocks.

---

## Project Context

**NuroSearch** is a custom Vector Database and RAG (Retrieval-Augmented Generation) engine built from scratch in Python (Flask). It already implements:
- HNSW graph (Hierarchical Navigable Small World) — from scratch, no libraries
- KD-Tree and Brute Force search algorithms
- BM25 lexical search
- Hybrid Search (70% vector + 30% BM25)
- Local RAG pipeline using Ollama (`nomic-embed-text` + `qwen2.5:0.5b`)
- SQLite persistence (`vectors.db`)
- Optional Redis caching
- Interactive 3D/2D frontend with Plotly

**Current resume score: 6.5/10** — solid initiative, but lacks scale, production design, and measurability.
**Target resume score after all features: 9.5/10** — competes with FAANG-level portfolios.

**Repository owner:** Prathamesh Jadhav (GitHub: `github.com/Prathamesh-Jadhav04`)

---

## Implementation Order (Do Exactly In This Sequence)

| # | Feature | Category | Resume Impact | Difficulty |
|---|---------|----------|---------------|------------|
| 1 | IVF-PQ Quantization Engine | Core Algorithms | 🔴 Critical | Medium |
| 2 | Automated Benchmark Suite | Validation | 🔴 Critical | Easy |
| 3 | Cross-Encoder Re-Ranking (RAG 2.0) | AI Engineering | 🔴 Critical | Easy |
| 4 | CI/CD Pipeline (GitHub Actions) | DevOps | 🟠 High | Easy |
| 5 | Docker Compose Setup | DevOps | 🟠 High | Easy |
| 6 | GPU-Accelerated Search | Core Systems | 🟠 High | Medium |
| 7 | Kafka Async Ingestion | MLOps | 🟡 Medium | Medium |
| 8 | Distributed Cluster + Raft | Systems | 🔴 Critical | Hard |
| 9 | GraphRAG with Neo4j | AI Engineering | 🟡 Medium | Hard |
| 10 | SQL-Like Query Language | Developer Tools | 🟢 Bonus | Hard |
| 11 | README + Demo GIF | Presentation | 🔴 Critical | Easy |
| 12 | Unit Tests + pytest Suite | Quality | 🟠 High | Easy |
| 13 | Technical Blog Post | Visibility | 🟠 High | Easy |

---

---

# FEATURE 01 — IVF-PQ Quantization Engine

## What It Is
IVF-PQ (Inverted File Index + Product Quantization) is the compression and indexing algorithm used by production vector databases like FAISS, Milvus, and Pinecone to search billion-scale databases within megabytes of memory. Right now NuroSearch stores raw float vectors (768 floats × 4 bytes = 3072 bytes per vector). IVF-PQ compresses this to ~8 bytes per vector — a 99.7% reduction.

## Goal
Add a new search mode to NuroSearch called `ivfpq` that:
1. Trains a quantization codebook on existing vectors using K-Means
2. Compresses all vectors using Product Quantization into byte codes
3. Searches using the compressed codes instead of raw floats
4. Benchmarks memory usage and search speed vs raw HNSW

## Exact Implementation Steps

### Step 1 — Create `ivfpq.py` in project root

```python
import numpy as np
from sklearn.cluster import MiniBatchKMeans

class IVFPQIndex:
    """
    Inverted File Index + Product Quantization.
    Compresses 768D float vectors into M byte codes using sub-vector clustering.
    
    Architecture:
      - IVF: K-Means partitions dataset into C clusters (coarse quantization)
      - PQ:  Each vector split into M sub-vectors, each sub-vector compressed to 1 byte
      - Search: Only probe nearest N_PROBE clusters, use lookup table for fast distance
    """
    
    def __init__(self, dim=768, M=8, C=256, n_probe=8):
        """
        Args:
            dim:     Vector dimensionality (768 for nomic-embed-text)
            M:       Number of sub-vector segments (dim must be divisible by M)
            C:       Number of IVF clusters (coarse quantizers)
            n_probe: How many IVF clusters to search at query time
        """
        self.dim = dim
        self.M = M                        # Number of PQ sub-spaces
        self.sub_dim = dim // M           # Dimension per sub-space (768//8 = 96)
        self.C = C                        # Number of IVF centroids
        self.n_probe = n_probe
        self.K = 256                      # Codebook size per sub-space (fits in 1 byte)
        
        self.ivf_quantizer = None         # Coarse K-Means (C centroids)
        self.pq_codebooks = None          # Shape: [M, K, sub_dim] — PQ codebooks
        self.inverted_lists = {}          # cluster_id -> list of (doc_id, pq_code)
        self.id_map = {}                  # index position -> original doc_id
        self.is_trained = False
    
    def train(self, vectors: np.ndarray):
        """
        Train IVF coarse quantizer and PQ codebooks on a set of vectors.
        Call this once when you have >= 1000 vectors. Re-train when dataset doubles.
        
        Args:
            vectors: np.ndarray shape [N, dim], float32
        """
        vectors = np.array(vectors, dtype=np.float32)
        
        # --- Stage 1: Train IVF coarse quantizer ---
        print(f"[IVF-PQ] Training IVF with {self.C} clusters on {len(vectors)} vectors...")
        self.ivf_quantizer = MiniBatchKMeans(n_clusters=self.C, random_state=42, batch_size=512)
        self.ivf_quantizer.fit(vectors)
        
        # --- Stage 2: Train PQ codebooks ---
        # Compute IVF residuals: vector - its nearest IVF centroid
        assignments = self.ivf_quantizer.predict(vectors)
        residuals = vectors - self.ivf_quantizer.cluster_centers_[assignments]
        
        print(f"[IVF-PQ] Training PQ codebooks: {self.M} sub-spaces × {self.K} codes...")
        self.pq_codebooks = np.zeros((self.M, self.K, self.sub_dim), dtype=np.float32)
        
        for m in range(self.M):
            # Extract sub-vectors for this sub-space
            sub_vecs = residuals[:, m * self.sub_dim : (m + 1) * self.sub_dim]
            kmeans = MiniBatchKMeans(n_clusters=self.K, random_state=42, batch_size=512)
            kmeans.fit(sub_vecs)
            self.pq_codebooks[m] = kmeans.cluster_centers_
        
        self.is_trained = True
        print("[IVF-PQ] Training complete.")
    
    def encode(self, vector: np.ndarray) -> np.ndarray:
        """
        Compress a single vector into M bytes using trained PQ codebooks.
        Returns: np.ndarray of shape [M], dtype uint8
        """
        assert self.is_trained, "Call train() before encode()"
        vector = np.array(vector, dtype=np.float32)
        
        # IVF assignment
        ivf_id = self.ivf_quantizer.predict(vector.reshape(1, -1))[0]
        residual = vector - self.ivf_quantizer.cluster_centers_[ivf_id]
        
        # PQ encode: for each sub-space, find nearest codebook entry
        code = np.zeros(self.M, dtype=np.uint8)
        for m in range(self.M):
            sub_vec = residual[m * self.sub_dim : (m + 1) * self.sub_dim]
            diffs = self.pq_codebooks[m] - sub_vec         # [K, sub_dim]
            distances = np.sum(diffs ** 2, axis=1)          # [K]
            code[m] = np.argmin(distances)
        
        return ivf_id, code
    
    def add(self, doc_id: int, vector: np.ndarray):
        """Add a single vector to the index after training."""
        ivf_id, pq_code = self.encode(vector)
        if ivf_id not in self.inverted_lists:
            self.inverted_lists[ivf_id] = []
        self.inverted_lists[ivf_id].append((doc_id, pq_code))
    
    def search(self, query_vector: np.ndarray, k: int = 5) -> list:
        """
        Search using ADC (Asymmetric Distance Computation).
        Returns: list of (doc_id, approximate_distance) sorted by distance
        """
        assert self.is_trained
        query = np.array(query_vector, dtype=np.float32)
        
        # Find nearest IVF clusters to probe
        dists_to_centroids = np.sum(
            (self.ivf_quantizer.cluster_centers_ - query) ** 2, axis=1
        )
        probe_clusters = np.argsort(dists_to_centroids)[:self.n_probe]
        
        # Build lookup table: distance from query sub-vectors to each codebook entry
        # Shape: [M, K] — precomputed once, reused for all candidates
        lookup_table = np.zeros((self.M, self.K), dtype=np.float32)
        for m in range(self.M):
            q_sub = query[m * self.sub_dim : (m + 1) * self.sub_dim]
            diffs = self.pq_codebooks[m] - q_sub            # [K, sub_dim]
            lookup_table[m] = np.sum(diffs ** 2, axis=1)
        
        # Score all candidates in probed clusters using lookup table (fast addition, not float mult)
        candidates = []
        for cluster_id in probe_clusters:
            for doc_id, pq_code in self.inverted_lists.get(cluster_id, []):
                # ADC: sum distances from lookup table for each sub-space code
                approx_dist = sum(lookup_table[m, pq_code[m]] for m in range(self.M))
                candidates.append((doc_id, float(approx_dist)))
        
        candidates.sort(key=lambda x: x[1])
        return candidates[:k]
    
    def memory_bytes(self) -> int:
        """Calculate total memory used by the compressed index."""
        total = 0
        for lists in self.inverted_lists.values():
            total += len(lists) * self.M  # M bytes per encoded vector
        return total
```

### Step 2 — Wire into `main.py`

Add to the `/search` endpoint's `algo` parameter choices:
```python
elif algo == 'ivfpq':
    if not ivfpq_index.is_trained:
        return jsonify({"error": "IVFPQ index not trained. Add more vectors first."}), 400
    results = ivfpq_index.search(query_vector, k=k)
```

Add a new endpoint `/ivfpq/train` (POST) that triggers training on all existing vectors.

Add `/ivfpq/stats` (GET) that returns:
```json
{
  "compressed_memory_bytes": 1638,
  "raw_memory_bytes": 2359296,
  "compression_ratio": "99.93%",
  "trained": true,
  "n_vectors": 512,
  "codebooks_M": 8,
  "clusters_C": 256
}
```

### Step 3 — Add to benchmark comparison panel in frontend

Show a 4th bar in the benchmark chart: HNSW vs KD-Tree vs Brute Force vs **IVF-PQ**. Also show a memory comparison panel alongside speed.

## What "Done" Looks Like
- `POST /ivfpq/train` trains the index on existing 768D document vectors
- `GET /search?algo=ivfpq` returns results using compressed codes
- `GET /ivfpq/stats` shows compression ratio (should be >90%)
- Frontend benchmark chart shows IVF-PQ speed and memory alongside other algorithms
- A test `tests/test_ivfpq.py` verifies that IVF-PQ recall is ≥ 0.75 (lower than HNSW is expected and acceptable)

## Resume Impact
**Before:** "Built a vector search engine with HNSW"
**After:** "Implemented IVF-PQ approximate nearest neighbor search with asymmetric distance computation, reducing index memory footprint by 99%+ and enabling sub-millisecond search on compressed 768-dimensional embeddings"

**Jobs this unlocks:** AI Infrastructure Engineer, ML Systems Engineer, Vector DB Engineer (Pinecone/Weaviate/Qdrant), Research Engineer

---

---

# FEATURE 02 — Automated Benchmark Suite (Recall@K, QPS, Memory)

## What It Is
A standalone Python script + CI gate that measures NuroSearch's search quality and performance with hard numbers. This is what separates "I built a vector DB" from "I measured my vector DB." Every production search system ships with benchmarks. NuroSearch should too.

## Goal
Build `tests/benchmark_gate.py` that:
1. Loads a standard test dataset (or generates one)
2. Measures Recall@K (search accuracy vs brute force ground truth)
3. Measures QPS (queries per second under concurrency)
4. Measures memory usage per 10K vectors
5. Fails CI if Recall@10 drops below 0.85 (regression gate)
6. Outputs a JSON report that gets saved as a CI artifact

## Exact Implementation Steps

### Step 1 — Create `tests/benchmark_gate.py`

```python
"""
NuroSearch Benchmark Gate
Runs on every CI push. Fails if Recall@10 < RECALL_THRESHOLD.
Also generates benchmark_report.json for artifact storage.
"""

import time
import json
import sys
import random
import threading
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hnsw import HNSWIndex          # Import your HNSW class
from kd_tree import KDTreeIndex     # Import your KD-Tree class

RECALL_THRESHOLD = 0.85
DIM = 16                            # Use 16D demo vectors for CI (fast)
N_VECTORS = 1000
N_QUERIES = 100
K = 10

def random_vector(dim):
    v = [random.gauss(0, 1) for _ in range(dim)]
    mag = sum(x**2 for x in v) ** 0.5
    return [x / mag for x in v]

def cosine_distance(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return 1.0 - dot

def brute_force_topk(vectors, query, k):
    scored = [(i, cosine_distance(query, v)) for i, v in enumerate(vectors)]
    scored.sort(key=lambda x: x[1])
    return [i for i, _ in scored[:k]]

def compute_recall(approx_results, exact_results, k):
    """Recall@K = |approx ∩ exact| / K"""
    return len(set(approx_results[:k]) & set(exact_results[:k])) / k

def measure_qps(search_fn, queries, k, duration_sec=5):
    """Run search_fn for duration_sec seconds, count queries completed."""
    count = 0
    start = time.time()
    idx = 0
    while time.time() - start < duration_sec:
        search_fn(queries[idx % len(queries)], k)
        count += 1
        idx += 1
    return count / duration_sec

def run_benchmarks():
    print("=" * 60)
    print("NuroSearch Benchmark Gate")
    print("=" * 60)

    # Generate dataset
    print(f"\nGenerating {N_VECTORS} random {DIM}D vectors...")
    vectors = [random_vector(DIM) for _ in range(N_VECTORS)]
    queries = [random_vector(DIM) for _ in range(N_QUERIES)]

    # Build HNSW index
    print("Building HNSW index...")
    hnsw = HNSWIndex(dim=DIM, M=16, ef_build=200)
    t0 = time.time()
    for i, v in enumerate(vectors):
        hnsw.insert(i, v)
    hnsw_build_time = time.time() - t0
    print(f"  HNSW build time: {hnsw_build_time:.3f}s")

    # Compute Recall@K
    print(f"\nComputing Recall@{K} over {N_QUERIES} queries...")
    recalls = []
    hnsw_latencies = []
    for q in queries:
        exact = brute_force_topk(vectors, q, K)
        t0 = time.perf_counter()
        approx = hnsw.search(q, K)
        hnsw_latencies.append((time.perf_counter() - t0) * 1e6)  # microseconds
        recalls.append(compute_recall(approx, exact, K))
    
    mean_recall = sum(recalls) / len(recalls)
    mean_latency_us = sum(hnsw_latencies) / len(hnsw_latencies)
    p99_latency_us = sorted(hnsw_latencies)[int(0.99 * len(hnsw_latencies))]

    print(f"  Recall@{K}:        {mean_recall:.4f}")
    print(f"  Mean latency:    {mean_latency_us:.1f} µs")
    print(f"  P99 latency:     {p99_latency_us:.1f} µs")

    # Measure QPS
    print(f"\nMeasuring QPS (5s window)...")
    qps = measure_qps(lambda q, k: hnsw.search(q, k), queries, K)
    print(f"  HNSW QPS:        {qps:.1f}")

    # Build report
    report = {
        "recall_at_k": round(mean_recall, 4),
        "k": K,
        "n_vectors": N_VECTORS,
        "n_queries": N_QUERIES,
        "hnsw_build_time_sec": round(hnsw_build_time, 3),
        "mean_latency_microsec": round(mean_latency_us, 1),
        "p99_latency_microsec": round(p99_latency_us, 1),
        "qps": round(qps, 1),
        "threshold": RECALL_THRESHOLD,
        "passed": mean_recall >= RECALL_THRESHOLD
    }

    # Save report
    with open("benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to benchmark_report.json")

    # CI Gate
    print("\n" + "=" * 60)
    if mean_recall < RECALL_THRESHOLD:
        print(f"FAIL: Recall@{K} = {mean_recall:.4f} < threshold {RECALL_THRESHOLD}")
        print("This means HNSW graph quality has degraded. Check M, ef_build parameters.")
        sys.exit(1)
    else:
        print(f"PASS: Recall@{K} = {mean_recall:.4f} >= threshold {RECALL_THRESHOLD}")
        sys.exit(0)

if __name__ == "__main__":
    run_benchmarks()
```

### Step 2 — Add benchmark results display to frontend

The frontend should fetch `/benchmark/report` (GET) and show:
- A card: "Recall@10: 0.923" with a green/red indicator
- A card: "QPS: 4821"
- A card: "P99 Latency: 312 µs"
- These numbers update live when benchmark is rerun from UI

### Step 3 — Save report as CI artifact

In `.github/workflows/ci.yml`:
```yaml
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: benchmark-report
    path: benchmark_report.json
```

## What "Done" Looks Like
- `python tests/benchmark_gate.py` runs in under 60 seconds
- CI fails automatically if Recall@10 drops below 0.85
- `benchmark_report.json` is uploaded as a GitHub Actions artifact on every run
- Frontend `/benchmark` panel shows live numbers from the report
- README shows a benchmark table with actual measured numbers

## Resume Impact
**Before:** "Implemented HNSW — fast approximate nearest neighbor search"
**After:** "Validated HNSW implementation with automated recall benchmarking (Recall@10: 0.93), P99 latency measurement, and QPS testing — CI gate rejects any commit that drops recall below 85%"

**Jobs this unlocks:** Any ML/AI infrastructure role that asks "how did you validate your system?" — this is a complete answer.

---

---

# FEATURE 03 — Cross-Encoder Re-Ranking (RAG 2.0)

## What It Is
Standard RAG uses a single embedding model (bi-encoder) to retrieve relevant chunks. The problem: bi-encoders compress both query and document into independent vectors, losing fine-grained interaction signals. Cross-encoders jointly encode (query, document) pairs and compute a precise relevance score. This is a two-stage pipeline: Stage 1 retrieves 20-50 candidates fast (HNSW), Stage 2 re-ranks precisely (cross-encoder). Used in production by Google, Bing, and every serious RAG system.

## Goal
Upgrade the `/doc/ask` endpoint to use two-stage retrieval:
1. Stage 1: Retrieve top-20 chunks using HNSW (existing code, just change k=3 → k=20)
2. Stage 2: Re-rank all 20 chunks using a cross-encoder, keep top-3
3. Feed top-3 re-ranked chunks to the LLM
4. Return `rerank_scores` in the API response for frontend display

## Exact Implementation Steps

### Step 1 — Install dependency

```bash
pip install sentence-transformers
```

Add to `requirements.txt`:
```
sentence-transformers>=2.7.0
```

### Step 2 — Create `reranker.py`

```python
"""
Cross-Encoder Re-Ranker for NuroSearch RAG pipeline.
Uses BAAI/bge-reranker-base from HuggingFace (runs locally, no API key needed).
Model size: ~280MB. Downloads once, cached in ~/.cache/huggingface/
"""

from sentence_transformers import CrossEncoder
import numpy as np

class CrossEncoderReranker:
    """
    Two-stage retrieval: 
      Stage 1 (caller): HNSW retrieves top-N candidates (fast, approximate)
      Stage 2 (this):   Cross-encoder re-ranks top-N precisely
    
    Model options (trade speed vs quality):
      - 'cross-encoder/ms-marco-MiniLM-L-6-v2'  → fastest, good quality (66MB)
      - 'BAAI/bge-reranker-base'                 → best quality (280MB)  ← recommended
      - 'jinaai/jina-reranker-v1-turbo-en'       → production-grade (need HF token)
    """
    
    def __init__(self, model_name='cross-encoder/ms-marco-MiniLM-L-6-v2'):
        print(f"[Reranker] Loading cross-encoder: {model_name}")
        self.model = CrossEncoder(model_name, max_length=512)
        print("[Reranker] Ready.")
    
    def rerank(self, query: str, candidates: list[dict], top_k: int = 3) -> list[dict]:
        """
        Re-rank candidate chunks by cross-encoder relevance score.
        
        Args:
            query:      The user's question (raw text string)
            candidates: List of dicts, each must have 'text' key with chunk content
            top_k:      How many to return after re-ranking
        
        Returns:
            List of top_k dicts from candidates, sorted by rerank_score descending.
            Each dict gets a new 'rerank_score' field added.
        
        Example:
            candidates = [
                {"doc_id": 1, "text": "The mitochondria is...", "hnsw_score": 0.82},
                {"doc_id": 2, "text": "Photosynthesis occurs...", "hnsw_score": 0.79},
                ... (20 total)
            ]
            reranked = reranker.rerank("What is the powerhouse of the cell?", candidates, top_k=3)
            # Returns top 3 with rerank_score added
        """
        if not candidates:
            return []
        
        # Build (query, document) pairs for cross-encoder
        pairs = [(query, c['text']) for c in candidates]
        
        # Score all pairs in one batch (cross-encoder sees both together)
        scores = self.model.predict(pairs)
        
        # Attach scores to candidates
        for i, candidate in enumerate(candidates):
            candidate['rerank_score'] = float(scores[i])
        
        # Sort by rerank score (higher = more relevant)
        candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return candidates[:top_k]
```

### Step 3 — Modify `/doc/ask` endpoint in `main.py`

```python
# In main.py, at module level:
from reranker import CrossEncoderReranker
reranker = CrossEncoderReranker()  # loads once on startup

# In /doc/ask endpoint:
@app.route('/doc/ask', methods=['POST'])
def doc_ask():
    data = request.json
    question = data.get('question', '')
    k_final = data.get('k', 3)          # How many chunks to feed LLM
    k_retrieve = data.get('k_retrieve', 20)  # How many to retrieve before reranking
    use_rerank = data.get('rerank', True)
    
    # Stage 1: Embed query and retrieve top-20 candidates
    query_embedding = embed_text(question)  # existing function
    raw_candidates = document_db.search(query_embedding, k=k_retrieve)
    
    # Stage 2: Re-rank if enabled
    if use_rerank and len(raw_candidates) > k_final:
        final_chunks = reranker.rerank(question, raw_candidates, top_k=k_final)
    else:
        final_chunks = raw_candidates[:k_final]
    
    # Assemble context from re-ranked chunks
    context = "\n\n".join([c['text'] for c in final_chunks])
    
    # Build prompt
    prompt = f"""You are a helpful assistant. Answer the question using ONLY the provided context.
    
Context:
{context}

Question: {question}
Answer:"""
    
    # Stream response (existing SSE logic)
    def generate():
        # Yield rerank metadata first
        import json
        meta = {
            "type": "metadata",
            "chunks_retrieved": len(raw_candidates),
            "chunks_after_rerank": len(final_chunks),
            "rerank_scores": [round(c.get('rerank_score', 0), 4) for c in final_chunks]
        }
        yield f"data: {json.dumps(meta)}\n\n"
        
        # Then stream LLM answer (existing Ollama SSE code)
        # ... existing streaming code here ...
    
    return Response(generate(), mimetype='text/event-stream')
```

### Step 4 — Frontend update

In the "Ask AI" panel, show:
- "Retrieved 20 chunks → Re-ranked → Using top 3"
- Small score badges on each source chunk: `[Rerank: 8.42]`

## What "Done" Looks Like
- `/doc/ask` with `"rerank": true` retrieves 20 chunks, re-ranks, feeds top 3 to LLM
- `/doc/ask` with `"rerank": false` uses original top-3 HNSW retrieval (for comparison)
- Response includes `rerank_scores` array in metadata SSE event
- Frontend shows re-rank scores alongside source chunks
- A test `tests/test_reranker.py` verifies that re-ranker correctly identifies the most relevant chunk in a synthetic test case

## Resume Impact
**Before:** "Built RAG pipeline using vector search"
**After:** "Engineered two-stage hybrid retrieval pipeline: bi-encoder HNSW first-stage recall (top-20) followed by cross-encoder neural re-ranking (top-3), mirroring production RAG systems at Google and Bing"

**Jobs this unlocks:** GenAI Engineer, RAG Engineer, Applied AI Engineer, LLM Systems Engineer

---

---

# FEATURE 04 — CI/CD Pipeline (GitHub Actions)

## What It Is
A fully automated quality gate that runs on every `git push` and pull request. No broken code reaches `main`. Includes linting, type checking, security scanning, tests, benchmark validation, Docker build, and deployment.

## Goal
Create `.github/workflows/ci.yml` that:
1. Lints with `ruff` and `black`
2. Type-checks with `mypy`
3. Security-scans with `bandit`
4. Runs all pytest tests with coverage
5. Runs benchmark gate (Recall@10 ≥ 0.85)
6. Builds and pushes Docker image to GHCR
7. Deploys to server on `main` branch pushes
8. Notifies on failure

## Exact Implementation Steps

### Step 1 — Create `.github/workflows/ci.yml`

```yaml
name: NuroSearch CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  IMAGE_NAME: ghcr.io/${{ github.repository_owner }}/nurosearch

jobs:
  # ─────────────────────────────────────────────
  # JOB 1: Lint, format, type check, security
  # ─────────────────────────────────────────────
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      
      - name: Install quality tools
        run: pip install ruff black mypy bandit
      
      - name: Ruff lint
        run: ruff check . --output-format=github
      
      - name: Black format check
        run: black --check --diff .
      
      - name: Mypy type check
        run: mypy main.py ivfpq.py reranker.py --ignore-missing-imports
      
      - name: Bandit security scan
        run: bandit -r . -x tests/ -ll  # only medium+ severity

  # ─────────────────────────────────────────────
  # JOB 2: Unit + Integration tests with coverage
  # ─────────────────────────────────────────────
  test:
    name: Tests
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      
      - name: Install dependencies
        run: pip install -r requirements.txt pytest pytest-cov
      
      - name: Run tests with coverage
        run: pytest tests/ -v --cov=. --cov-report=xml --cov-report=term-missing
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.xml
          fail_ci_if_error: false  # don't fail if codecov is down

  # ─────────────────────────────────────────────
  # JOB 3: Benchmark gate (recall regression check)
  # ─────────────────────────────────────────────
  benchmark:
    name: Benchmark Gate
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      
      - name: Install dependencies
        run: pip install -r requirements.txt numpy
      
      - name: Run benchmark gate
        run: python tests/benchmark_gate.py
      
      - name: Upload benchmark report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: benchmark-report-${{ github.sha }}
          path: benchmark_report.json

  # ─────────────────────────────────────────────
  # JOB 4: Docker build + push (main branch only)
  # ─────────────────────────────────────────────
  docker:
    name: Docker Build & Push
    needs: benchmark
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - uses: docker/setup-buildx-action@v3
      
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.IMAGE_NAME }}:latest
            ${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ─────────────────────────────────────────────
  # JOB 5: Deploy (main branch, after docker push)
  # ─────────────────────────────────────────────
  deploy:
    name: Deploy
    needs: docker
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            cd /opt/nurosearch
            docker pull ghcr.io/prathamesh-jadhav04/nurosearch:latest
            docker compose down
            docker compose up -d
            docker system prune -f
```

### Step 2 — Create `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 nurosearch && chown -R nurosearch:nurosearch /app
USER nurosearch

EXPOSE 8080

CMD ["python", "main.py"]
```

### Step 3 — Add GitHub repository secrets

In GitHub repo → Settings → Secrets and variables → Actions, add:
- `CODECOV_TOKEN` — from codecov.io (free for public repos)
- `DEPLOY_HOST` — your VPS IP
- `DEPLOY_USER` — `ubuntu` or your SSH user
- `DEPLOY_KEY` — private SSH key for server access

### Step 4 — Add CI status badges to README

```markdown
[![CI](https://github.com/Prathamesh-Jadhav04/NuroSearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Prathamesh-Jadhav04/NuroSearch/actions)
[![codecov](https://codecov.io/gh/Prathamesh-Jadhav04/NuroSearch/branch/main/graph/badge.svg)](https://codecov.io/gh/Prathamesh-Jadhav04/NuroSearch)
```

## What "Done" Looks Like
- Every `git push` triggers the pipeline automatically
- PRs cannot be merged if any job fails (set branch protection rules in GitHub)
- A green "CI passing" badge appears on README
- `docker pull ghcr.io/prathamesh-jadhav04/nurosearch:latest` works from anywhere
- CI run logs are publicly visible (for recruiters to inspect)

## Resume Impact
**Before:** "Built and deployed a Flask application"
**After:** "Implemented full CI/CD pipeline: automated lint/type-check/security scan → pytest with coverage → HNSW recall regression gate → Docker image build and GHCR push → zero-downtime SSH deployment. Branch protection enforces green CI on all merges."

**Jobs this unlocks:** Any backend/ML engineering role. CI/CD is a baseline expectation at every company with engineering standards. Having it makes you look senior.

---

---

# FEATURE 05 — Docker Compose Setup

## What It Is
One command (`docker compose up`) that spins up the entire NuroSearch stack: Flask app + Redis + optional Kafka. No manual environment setup. This makes the project immediately runnable by anyone — recruiters, collaborators, interviewers.

## Goal
Create `docker-compose.yml` that starts:
- `nurosearch` — Flask app on port 8080
- `redis` — Cache on port 6379
- `kafka` + `zookeeper` — Message broker on port 9092 (optional profile)

## Exact Implementation Steps

### Step 1 — Create `docker-compose.yml`

```yaml
version: '3.9'

services:
  nurosearch:
    build: .
    image: ghcr.io/prathamesh-jadhav04/nurosearch:latest
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
      - KAFKA_BOOTSTRAP=kafka:9092
      - OLLAMA_BASE_URL=http://host.docker.internal:11434  # Ollama runs on host
    volumes:
      - ./data:/app/data           # SQLite persistence
      - ./benchmark_report.json:/app/benchmark_report.json
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/stats"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes  # persistence enabled
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Optional: start with `docker compose --profile kafka up`
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    profiles: [kafka]
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    restart: unless-stopped

  kafka:
    image: confluentinc/cp-kafka:7.6.0
    profiles: [kafka]
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    depends_on: [zookeeper]
    restart: unless-stopped

volumes:
  redis_data:
```

### Step 2 — Add `.env.example`

```env
# Copy to .env and fill in values
REDIS_URL=redis://localhost:6379
OLLAMA_BASE_URL=http://localhost:11434
KAFKA_BOOTSTRAP=localhost:9092
FLASK_ENV=production
```

### Step 3 — Update README with one-command startup

```markdown
## Quick Start

```bash
# 1. Start Ollama separately (needed for embeddings)
ollama pull nomic-embed-text
ollama pull qwen2.5:0.5b
ollama serve

# 2. Start NuroSearch stack
docker compose up

# 3. Open browser
open http://localhost:8080

# Optional: start with Kafka support
docker compose --profile kafka up
```

## What "Done" Looks Like
- `docker compose up` starts everything in under 60 seconds
- `http://localhost:8080` loads the dashboard
- Redis cache is connected automatically
- Volumes persist SQLite data between container restarts
- `docker compose --profile kafka up` adds Kafka broker

## Resume Impact
This is a professionalism signal. It shows you think about reproducibility and onboarding, not just "it works on my machine."

---

---

# FEATURE 06 — GPU-Accelerated Search (PyTorch/CUDA)

## What It Is
Offload cosine similarity computation from CPU Python loops to GPU matrix multiplication. On a GPU, computing distances to 100,000 vectors can happen 30-100x faster than CPU because all comparisons run in parallel using CUDA cores.

## Goal
Add a `gpu` algo option to `/search` that:
1. Loads all index vectors into a PyTorch CUDA tensor (GPU memory)
2. Computes cosine similarity using `torch.mm()` — one matrix multiply, all comparisons at once
3. Returns top-K results using `torch.topk()`
4. Falls back to CPU tensors if no GPU is available (still faster than raw Python loops)

## Exact Implementation Steps

### Step 1 — Create `gpu_search.py`

```python
"""
GPU-Accelerated Vector Search using PyTorch.
Falls back to CPU tensors if CUDA is not available (still ~3x faster than Python loops).
"""

import torch
import numpy as np

class GPUSearchIndex:
    """
    Maintains a matrix of all index vectors on GPU memory.
    Supports batched cosine similarity using matrix multiplication.
    
    Memory model:
        - Each vector: dim × 4 bytes (float32)
        - 10,000 × 768D vectors = ~29MB GPU memory (negligible)
        - 1,000,000 × 768D vectors = ~2.9GB GPU memory (fits on most GPUs)
    """
    
    def __init__(self, dim: int):
        self.dim = dim
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.index_tensor = None     # Shape: [N, dim] on device
        self.id_map = []             # Maps row index → original doc_id
        
        print(f"[GPU Search] Using device: {self.device}")
        if self.device.type == 'cuda':
            props = torch.cuda.get_device_properties(0)
            print(f"[GPU Search] GPU: {props.name}, VRAM: {props.total_memory / 1e9:.1f}GB")
    
    def build(self, vectors: list[tuple[int, list[float]]]):
        """
        Build GPU index from (doc_id, vector) pairs.
        Normalizes all vectors for cosine similarity via dot product.
        
        Args:
            vectors: List of (doc_id, vector) tuples
        """
        if not vectors:
            return
        
        self.id_map = [doc_id for doc_id, _ in vectors]
        matrix = np.array([v for _, v in vectors], dtype=np.float32)
        
        # Move to GPU and normalize (so dot product = cosine similarity)
        tensor = torch.from_numpy(matrix).to(self.device)
        norms = torch.norm(tensor, dim=1, keepdim=True).clamp(min=1e-8)
        self.index_tensor = tensor / norms  # L2-normalized
        
        print(f"[GPU Search] Index built: {len(vectors)} vectors on {self.device}")
    
    def add(self, doc_id: int, vector: list[float]):
        """Add a single vector to the GPU index."""
        v = torch.tensor(vector, dtype=torch.float32, device=self.device)
        v = v / v.norm().clamp(min=1e-8)
        v = v.unsqueeze(0)  # [1, dim]
        
        if self.index_tensor is None:
            self.index_tensor = v
        else:
            self.index_tensor = torch.cat([self.index_tensor, v], dim=0)
        
        self.id_map.append(doc_id)
    
    def search(self, query_vector: list[float], k: int = 5) -> list[tuple[int, float]]:
        """
        GPU cosine similarity search.
        
        Speed: 
          CPU (Python loops): ~50ms for 10K vectors
          CPU (PyTorch):      ~2ms for 10K vectors  
          GPU (CUDA):         ~0.1ms for 10K vectors (500x speedup)
        
        Returns: list of (doc_id, cosine_similarity_score) sorted descending
        """
        if self.index_tensor is None or len(self.id_map) == 0:
            return []
        
        k = min(k, len(self.id_map))
        
        # Normalize query
        q = torch.tensor(query_vector, dtype=torch.float32, device=self.device)
        q = q / q.norm().clamp(min=1e-8)
        q = q.unsqueeze(0)  # [1, dim]
        
        # Matrix multiply: [1, dim] × [dim, N] = [1, N] similarity scores
        # This is the key operation — one GPU kernel call, fully parallel
        similarities = torch.mm(q, self.index_tensor.T).squeeze(0)  # [N]
        
        # Get top-K in one call
        top_scores, top_indices = torch.topk(similarities, k=k)
        
        # Move back to CPU for result assembly
        top_scores = top_scores.cpu().numpy()
        top_indices = top_indices.cpu().numpy()
        
        results = []
        for idx, score in zip(top_indices, top_scores):
            results.append((self.id_map[int(idx)], float(score)))
        
        return results
    
    def batch_search(self, queries: list[list[float]], k: int = 5) -> list[list[tuple]]:
        """
        Search multiple queries in one GPU call.
        Key advantage of GPU: batch of 100 queries costs nearly the same as 1.
        
        Returns: list of result lists, one per query
        """
        if not queries or self.index_tensor is None:
            return [[] for _ in queries]
        
        k = min(k, len(self.id_map))
        
        # Stack all queries into matrix
        q_matrix = torch.tensor(queries, dtype=torch.float32, device=self.device)
        norms = torch.norm(q_matrix, dim=1, keepdim=True).clamp(min=1e-8)
        q_matrix = q_matrix / norms  # [B, dim]
        
        # [B, dim] × [dim, N] = [B, N] — all queries vs all index vectors at once
        all_similarities = torch.mm(q_matrix, self.index_tensor.T)  # [B, N]
        
        top_scores, top_indices = torch.topk(all_similarities, k=k, dim=1)
        top_scores = top_scores.cpu().numpy()
        top_indices = top_indices.cpu().numpy()
        
        batch_results = []
        for b in range(len(queries)):
            results = [(self.id_map[int(top_indices[b, i])], float(top_scores[b, i])) for i in range(k)]
            batch_results.append(results)
        
        return batch_results
    
    def memory_bytes(self) -> int:
        if self.index_tensor is None:
            return 0
        return self.index_tensor.element_size() * self.index_tensor.nelement()
```

### Step 2 — Add to `/search` and `/benchmark` endpoints

```python
# In main.py, at module level:
from gpu_search import GPUSearchIndex
gpu_index = GPUSearchIndex(dim=16)  # 16D for demo; 768D for doc search

# In /benchmark endpoint, add GPU timing:
import time
t0 = time.perf_counter()
gpu_results = gpu_index.search(query_vector, k=k)
gpu_time_us = (time.perf_counter() - t0) * 1e6

# Return alongside HNSW, KD-Tree, Brute Force timings
```

### Step 3 — Add GPU memory stats to `/stats` endpoint

```json
{
  "gpu": {
    "available": true,
    "device": "NVIDIA GeForce RTX 3060",
    "index_memory_mb": 0.024,
    "n_vectors": 1024
  }
}
```

## What "Done" Looks Like
- `/search?algo=gpu` works on CPU and GPU (auto-detected)
- `/benchmark` panel shows 4th column: GPU search time in microseconds
- `batch_search()` method works correctly and is faster than N individual searches
- README notes GPU vs CPU benchmark numbers (even CPU-tensor mode shows improvement)

## Resume Impact
**Before:** "Python vector search implementation"
**After:** "Implemented GPU-accelerated similarity search using PyTorch CUDA — matrix multiplication over 768D embeddings achieves sub-millisecond latency; batch search amortizes GPU memory transfer across queries for throughput optimization"

**Note:** If no GPU is available, CPU tensor mode still shows ~3x speedup over pure Python loops — still worth implementing and benchmarking.

**Jobs this unlocks:** ML Infrastructure Engineer, AI Systems Engineer, GPU Computing roles

---

---

# FEATURE 07 — Kafka Async Document Ingestion

## What It Is
Right now, when a user uploads a PDF to `/doc/upload`, the Flask request thread is blocked while PyMuPDF extracts text, Ollama generates embeddings (can take 10-30 seconds for large docs), and HNSW indexes the chunks. If two users upload simultaneously, one request times out. Kafka separates the upload (fast) from the processing (slow and async).

## Goal
Modify `/doc/upload` to be instant (just publish to Kafka, return immediately), while a separate Python worker process consumes the Kafka topic and does all heavy lifting in the background.

## Exact Implementation Steps

### Step 1 — Create `ingestion_worker.py`

```python
"""
NuroSearch Document Ingestion Worker
Runs as a separate process alongside Flask.
Consumes document upload events from Kafka and processes them asynchronously.

Start with: python ingestion_worker.py
"""

import json
import time
import logging
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [Worker] %(message)s')
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = 'localhost:9092'
INGEST_TOPIC = 'nurosearch-document-ingestion'
STATUS_TOPIC = 'nurosearch-document-status'


def chunk_text(text: str, chunk_size: int = 250) -> list[str]:
    """Split text into chunks of ~chunk_size words with 50-word overlap."""
    words = text.split()
    chunks = []
    step = chunk_size - 50  # 50-word overlap between chunks
    for i in range(0, len(words), step):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def embed_text(text: str) -> list[float]:
    """Call local Ollama for embedding. Same as Flask app."""
    import requests
    response = requests.post('http://localhost:11434/api/embeddings', json={
        'model': 'nomic-embed-text',
        'prompt': text
    })
    return response.json()['embedding']


def process_document(event: dict, producer: KafkaProducer):
    """
    Full document processing pipeline:
    1. Chunk text
    2. Embed each chunk via Ollama
    3. Insert into DocumentDB HNSW index
    4. Publish status update to STATUS_TOPIC
    """
    doc_id = event['doc_id']
    title = event['title']
    text = event['text']
    
    logger.info(f"Processing document: {title} (id={doc_id})")
    
    # Publish "processing" status
    producer.send(STATUS_TOPIC, {
        'doc_id': doc_id, 'status': 'processing', 'progress': 0
    })
    
    chunks = chunk_text(text)
    logger.info(f"  Split into {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        try:
            embedding = embed_text(chunk)
            
            # Import and use the same DocumentDB instance
            # In production, use shared SQLite or a proper message for DB insert
            from main import document_db
            document_db.insert(doc_id=f"{doc_id}_{i}", title=title, text=chunk, embedding=embedding)
            
            progress = int((i + 1) / len(chunks) * 100)
            producer.send(STATUS_TOPIC, {
                'doc_id': doc_id, 'status': 'processing', 
                'progress': progress, 'chunk': i + 1, 'total': len(chunks)
            })
            logger.info(f"  Chunk {i+1}/{len(chunks)} indexed")
            
        except Exception as e:
            logger.error(f"  Failed chunk {i}: {e}")
            producer.send(STATUS_TOPIC, {
                'doc_id': doc_id, 'status': 'error', 'error': str(e)
            })
    
    producer.send(STATUS_TOPIC, {
        'doc_id': doc_id, 'status': 'complete', 'progress': 100, 'n_chunks': len(chunks)
    })
    logger.info(f"Document {title} processing complete ({len(chunks)} chunks)")


def run_worker():
    logger.info("NuroSearch Ingestion Worker starting...")
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP}...")
    
    consumer = KafkaConsumer(
        INGEST_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id='nurosearch-ingest-workers',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True
    )
    
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    logger.info(f"Listening on topic: {INGEST_TOPIC}")
    
    for message in consumer:
        event = message.value
        logger.info(f"Received ingestion event: {event.get('title', 'unknown')}")
        try:
            process_document(event, producer)
        except Exception as e:
            logger.error(f"Worker error: {e}")

if __name__ == '__main__':
    run_worker()
```

### Step 2 — Modify `/doc/upload` in `main.py`

```python
# Add at module level:
from kafka import KafkaProducer
import json
import uuid

kafka_producer = None
try:
    kafka_producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    print("[Kafka] Producer connected")
except Exception as e:
    print(f"[Kafka] Not available, using synchronous mode: {e}")

# Modify /doc/upload endpoint:
@app.route('/doc/upload', methods=['POST'])
def doc_upload():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file provided"}), 400
    
    # Extract text (existing logic)
    text = extract_text_from_file(file)
    title = file.filename
    doc_id = str(uuid.uuid4())
    
    if kafka_producer:
        # ASYNC path: publish and return immediately
        kafka_producer.send('nurosearch-document-ingestion', {
            'doc_id': doc_id,
            'title': title,
            'text': text
        })
        return jsonify({
            "status": "queued",
            "doc_id": doc_id,
            "message": "Document queued for async processing",
            "poll_url": f"/doc/status/{doc_id}"
        }), 202  # 202 Accepted (not 200 — processing not complete yet)
    else:
        # SYNC fallback: existing blocking logic
        process_document_sync(title, text)
        return jsonify({"status": "indexed", "doc_id": doc_id}), 200

# Add status polling endpoint:
@app.route('/doc/status/<doc_id>')
def doc_status(doc_id):
    # Read latest status from Redis or in-memory dict
    status = redis_client.get(f"doc_status:{doc_id}")
    return jsonify(json.loads(status) if status else {"status": "unknown"})
```

## What "Done" Looks Like
- `/doc/upload` returns `202 Accepted` in < 200ms (no blocking)
- `python ingestion_worker.py` runs separately and processes documents
- Frontend shows real-time progress: "Indexing: chunk 3/12..."
- Kafka consumer group allows multiple workers (horizontal scaling)
- Falls back gracefully to sync mode if Kafka is not running

## Resume Impact
**Before:** "PDF upload endpoint that indexes documents"
**After:** "Event-driven document ingestion pipeline using Apache Kafka — upload endpoint publishes to `nurosearch-document-ingestion` topic (202 Accepted in <200ms), consumer workers handle chunking, embedding, and HNSW indexing asynchronously with real-time progress via Redis"

**Jobs this unlocks:** MLOps Engineer, AI Platform Engineer, Backend Engineer (any company with ML pipelines)

---

---

# FEATURE 08 — Distributed Vector Cluster + Raft Consensus

## What It Is
The hardest feature. Transform NuroSearch from a single-node Flask app into a 3-node distributed vector database with consistent hashing for data sharding, scatter-gather search, and Raft consensus for write consistency. This is what production systems like Pinecone, Weaviate, and Qdrant do internally.

## Goal
Build a 3-node cluster where:
1. A coordinator node routes requests using consistent hashing
2. Worker nodes each hold a shard of the vector index
3. Search queries fan out to all workers, results merge at coordinator
4. Raft consensus ensures all nodes agree on writes before confirming

## Exact Implementation Steps

### Step 1 — Create `coordinator.py`

```python
"""
NuroSearch Coordinator Node
Routes INSERT and SEARCH requests across worker nodes using consistent hashing.
Implements scatter-gather for search queries.
"""

import hashlib
import asyncio
import aiohttp
from flask import Flask, request, jsonify

app = Flask(__name__)

# Worker node registry
WORKERS = [
    {"id": "worker-1", "url": "http://localhost:8081", "alive": True},
    {"id": "worker-2", "url": "http://localhost:8082", "alive": True},
    {"id": "worker-3", "url": "http://localhost:8083", "alive": True},
]

def get_worker_for_id(doc_id: str) -> dict:
    """
    Consistent hashing: map doc_id to a specific worker node.
    Same doc_id always routes to the same worker (stable sharding).
    """
    hash_value = int(hashlib.md5(str(doc_id).encode()).hexdigest(), 16)
    alive_workers = [w for w in WORKERS if w["alive"]]
    return alive_workers[hash_value % len(alive_workers)]

@app.route('/insert', methods=['POST'])
def coordinator_insert():
    """Route insert to the correct worker based on doc_id hashing."""
    data = request.json
    doc_id = data.get('doc_id') or data.get('id')
    
    worker = get_worker_for_id(str(doc_id))
    
    # Forward to worker
    import requests as req
    response = req.post(f"{worker['url']}/insert", json=data)
    return jsonify(response.json()), response.status_code

@app.route('/search', methods=['GET'])
def coordinator_search():
    """Scatter search to all workers, gather results, merge top-K."""
    params = request.args
    k = int(params.get('k', 5))
    
    # Scatter: query all workers in parallel
    import requests as req
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    all_results = []
    
    def query_worker(worker):
        try:
            response = req.get(f"{worker['url']}/search", params=params, timeout=5)
            return response.json().get('results', [])
        except Exception as e:
            worker['alive'] = False
            return []
    
    alive_workers = [w for w in WORKERS if w["alive"]]
    
    with ThreadPoolExecutor(max_workers=len(alive_workers)) as executor:
        futures = {executor.submit(query_worker, w): w for w in alive_workers}
        for future in as_completed(futures):
            all_results.extend(future.result())
    
    # Gather: merge and return global top-K
    all_results.sort(key=lambda x: x.get('score', float('inf')))
    merged = all_results[:k]
    
    return jsonify({"results": merged, "nodes_queried": len(alive_workers)})

if __name__ == '__main__':
    app.run(port=8080)
```

### Step 2 — Create `worker.py`

Each worker is a full NuroSearch node that only holds its shard of the data:

```python
"""
NuroSearch Worker Node
Holds a shard of the vector index. Receives forwarded requests from coordinator.
Run 3 instances: python worker.py --port 8081 --node-id worker-1
"""

import argparse
from flask import Flask, request, jsonify

# Import existing NuroSearch components
from hnsw import HNSWIndex
from bm25 import BM25Scorer

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8081)
parser.add_argument('--node-id', type=str, default='worker-1')
args = parser.parse_args()

app = Flask(__name__)
local_index = HNSWIndex(dim=16)  # Each worker has its own HNSW graph

@app.route('/insert', methods=['POST'])
def worker_insert():
    data = request.json
    local_index.insert(data['id'], data['embedding'], data.get('metadata', {}))
    return jsonify({"status": "inserted", "node": args.node_id})

@app.route('/search', methods=['GET'])
def worker_search():
    v = [float(x) for x in request.args.get('v', '').split(',')]
    k = int(request.args.get('k', 5))
    results = local_index.search(v, k=k)
    return jsonify({"results": results, "node": args.node_id})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "node": args.node_id, "vectors": len(local_index)})

if __name__ == '__main__':
    app.run(port=args.port)
```

### Step 3 — Add Raft consensus (simplified)

For the Raft implementation, use the `pysyncobj` library which provides a Python Raft implementation:

```bash
pip install pysyncobj
```

```python
from pysyncobj import SyncObj, replicated

class ReplicatedVectorLog(SyncObj):
    """
    Raft-replicated write log for NuroSearch.
    Ensures all 3 nodes agree on every insert before confirming to client.
    """
    
    def __init__(self, selfAddr, partnerAddrs):
        super().__init__(selfAddr, partnerAddrs)
        self._log = []      # Committed vector operations
    
    @replicated
    def append_insert(self, doc_id, embedding, metadata):
        """This method runs on ALL nodes via Raft consensus."""
        self._log.append({
            'op': 'insert',
            'doc_id': doc_id,
            'embedding': embedding,
            'metadata': metadata
        })
        # Apply to local HNSW index
        local_index.insert(doc_id, embedding, metadata)
    
    def get_log_size(self):
        return len(self._log)

# Initialize on each worker:
raft = ReplicatedVectorLog(
    selfAddr=f'localhost:{args.port + 100}',          # Raft port
    partnerAddrs=['localhost:8181', 'localhost:8182', 'localhost:8183']
)
```

### Step 4 — Docker Compose for cluster

```yaml
# Add to docker-compose.yml:
  worker-1:
    build: .
    command: python worker.py --port 8081 --node-id worker-1
    ports: ["8081:8081"]
  
  worker-2:
    build: .
    command: python worker.py --port 8082 --node-id worker-2
    ports: ["8082:8082"]
  
  worker-3:
    build: .
    command: python worker.py --port 8083 --node-id worker-3
    ports: ["8083:8083"]
  
  coordinator:
    build: .
    command: python coordinator.py
    ports: ["8080:8080"]
    depends_on: [worker-1, worker-2, worker-3]
```

## What "Done" Looks Like
- `docker compose up` starts coordinator + 3 workers
- Inserting 1000 vectors via coordinator distributes ~333 to each worker
- Search query returns merged results from all 3 workers
- Killing one worker: remaining 2 workers still serve queries (fault tolerance)
- Raft ensures insert is committed on majority (2 of 3) before returning 200

## Resume Impact
**Before:** "Single-node Flask API"
**After:** "Designed and implemented a distributed vector database with consistent hashing for data sharding, scatter-gather query routing, and Raft consensus for write durability — inspired by Pinecone's pod-based architecture"

**Jobs this unlocks:** Distributed Systems Engineer, Database Engineer, AI Infrastructure Engineer, Staff/Senior Engineer roles

---

---

# FEATURE 09 — GraphRAG with Neo4j Knowledge Graph

## What It Is
Standard RAG hallucinates on multi-hop questions like "Who is the CEO of the company that acquired the startup founded by the author of this document?" Vector search can't answer this — it needs to follow relationships. GraphRAG combines vector retrieval with knowledge graph traversal to answer complex relational queries without hallucination.

## Goal
When a document is ingested, extract entity-relationship triples and store in Neo4j. At query time, combine vector search (find starting nodes) with graph traversal (follow relationships) to answer multi-hop questions.

## Exact Implementation Steps

### Step 1 — Start Neo4j locally

```bash
# Via Docker:
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/nurosearch \
  neo4j:5

# Web UI at http://localhost:7474
```

### Step 2 — Create `knowledge_graph.py`

```python
"""
NuroSearch Knowledge Graph Integration
Extracts entity-relationship triples from documents and stores in Neo4j.
Used for multi-hop reasoning in GraphRAG queries.
"""

from neo4j import GraphDatabase
import requests

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "nurosearch")
OLLAMA_URL = "http://localhost:11434/api/generate"

class KnowledgeGraph:
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    
    def extract_triples(self, text: str, title: str) -> list[dict]:
        """
        Use local LLM to extract (subject, relation, object) triples from text.
        Returns list of {"subject": ..., "relation": ..., "object": ...}
        """
        prompt = f"""Extract all factual relationships from this text as JSON triples.
        
Text: {text[:2000]}

Return ONLY a JSON array like:
[
  {{"subject": "Tim Cook", "relation": "CEO_OF", "object": "Apple"}},
  {{"subject": "Apple", "relation": "FOUNDED_IN", "object": "1976"}}
]

Rules:
- Subject and Object must be specific entities (people, companies, places, dates)
- Relation must be a verb phrase in UPPERCASE_SNAKE_CASE
- Return only the JSON array, no other text"""
        
        response = requests.post(OLLAMA_URL, json={
            "model": "qwen2.5:0.5b",
            "prompt": prompt,
            "stream": False
        })
        
        import json, re
        raw = response.json().get('response', '[]')
        # Extract JSON array from response
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return []
        return []
    
    def store_triples(self, triples: list[dict], source_doc: str):
        """Store triples as Neo4j nodes and edges."""
        with self.driver.session() as session:
            for triple in triples:
                session.run("""
                    MERGE (s:Entity {name: $subject})
                    MERGE (o:Entity {name: $object})
                    MERGE (s)-[r:RELATION {type: $relation, source: $source}]->(o)
                """, 
                subject=triple['subject'],
                object=triple['object'],
                relation=triple['relation'],
                source=source_doc
                )
    
    def graph_search(self, start_entity: str, hops: int = 2) -> list[dict]:
        """
        Traverse from start_entity up to N hops, return all connected facts.
        Used to enrich RAG context with relational information.
        """
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH path = (start:Entity {{name: $name}})-[*1..{hops}]-(connected)
                RETURN start.name, 
                       [r in relationships(path) | r.type] AS relations,
                       [n in nodes(path) | n.name] AS entities
                LIMIT 20
            """, name=start_entity)
            
            paths = []
            for record in result:
                # Format as natural language: "Tim Cook CEO_OF Apple FOUNDED_BY Steve Jobs"
                entities = record['entities']
                relations = record['relations']
                path_str = entities[0]
                for i, rel in enumerate(relations):
                    path_str += f" --[{rel}]--> {entities[i+1]}"
                paths.append({"path": path_str, "entities": entities})
            
            return paths
    
    def hybrid_rag_context(self, question: str, vector_chunks: list[str]) -> str:
        """
        Combine vector chunks with graph paths for richer LLM context.
        1. Extract key entities from question using NER
        2. Traverse graph from those entities
        3. Append graph paths to vector context
        """
        # Simple entity extraction: capitalized words in question
        import re
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', question)
        
        graph_facts = []
        for entity in entities[:3]:  # Limit to 3 entities
            paths = self.graph_search(entity, hops=2)
            graph_facts.extend([p['path'] for p in paths[:5]])
        
        # Build combined context
        vector_context = "\n\n".join(vector_chunks)
        graph_context = "\n".join(graph_facts) if graph_facts else "No graph facts found."
        
        return f"""DOCUMENT CONTEXT:
{vector_context}

KNOWLEDGE GRAPH FACTS:
{graph_context}"""
```

### Step 3 — Add GraphRAG endpoint

```python
@app.route('/doc/ask/graph', methods=['POST'])
def doc_ask_graph():
    """GraphRAG: combines vector retrieval + knowledge graph traversal."""
    data = request.json
    question = data.get('question', '')
    
    # Stage 1: Vector retrieval (existing)
    vector_chunks = get_vector_chunks(question, k=5)
    
    # Stage 2: Graph context enrichment (new)
    combined_context = kg.hybrid_rag_context(question, vector_chunks)
    
    # Stage 3: LLM with enriched context (stream)
    # ... existing SSE streaming code ...
```

## What "Done" Looks Like
- Document ingestion automatically extracts and stores triples in Neo4j
- `/doc/ask/graph` uses both vector + graph context
- Neo4j browser at `http://localhost:7474` shows the knowledge graph visually
- A demo shows multi-hop question correctly answered (e.g., "Who founded the company that makes X?" where X was mentioned in a document)

## Resume Impact
**After:** "Implemented GraphRAG system combining HNSW vector retrieval with Neo4j knowledge graph traversal for multi-hop reasoning — entity-relationship triple extraction via local LLM enables relational Q&A beyond pure semantic similarity"

**Jobs this unlocks:** AI Research Engineer, GenAI Engineer at companies building enterprise RAG systems

---

---

# FEATURE 10 — SQL-Like Query Language Parser

## What It Is
A custom domain-specific language (DSL) that lets users query NuroSearch using familiar SQL-like syntax instead of raw API calls. Shows compiler theory knowledge (lexer → parser → AST → query plan → execution) — rare skill for an AI engineer.

## Goal
Parse and execute queries like:
```sql
SELECT * FROM documents WHERE category = 'sports' AND similarity > 0.82 LIMIT 5;
SEARCH vectors USING hnsw WHERE dim = 16 TOP 10;
```

## Exact Implementation Steps

### Step 1 — Install parser toolkit

```bash
pip install sly
```

### Step 2 — Create `query_parser.py`

```python
"""
NuroSearch Query Language Parser
Supports SQL-like syntax for vector search operations.
Uses SLY (Python Lex-Yacc) for lexing and parsing.
"""

from sly import Lexer, Parser

class NuroLexer(Lexer):
    """Tokenizer for NuroSearch Query Language."""
    
    tokens = {
        SELECT, FROM, WHERE, AND, OR, LIMIT, TOP,
        SEARCH, USING, ORDER, BY, ASC, DESC,
        EQ, NEQ, GT, LT, GTE, LTE,
        IDENT, NUMBER, STRING, STAR
    }
    ignore = ' \t'
    ignore_comment = r'\#.*'
    
    # Keywords
    SELECT  = r'SELECT'
    FROM    = r'FROM'
    WHERE   = r'WHERE'
    AND     = r'AND'
    OR      = r'OR'
    LIMIT   = r'LIMIT'
    TOP     = r'TOP'
    SEARCH  = r'SEARCH'
    USING   = r'USING'
    ORDER   = r'ORDER'
    BY      = r'BY'
    ASC     = r'ASC'
    DESC    = r'DESC'
    
    # Operators
    GTE = r'>='
    LTE = r'<='
    NEQ = r'!='
    GT  = r'>'
    LT  = r'<'
    EQ  = r'='
    
    STAR   = r'\*'
    IDENT  = r'[a-zA-Z_][a-zA-Z0-9_]*'
    NUMBER = r'\d+(\.\d+)?'
    STRING = r"'[^']*'"
    
    ignore_newline = r'\n+'

class NuroParser(Parser):
    tokens = NuroLexer.tokens
    
    @_('SELECT fields FROM IDENT where_clause limit_clause')
    def statement(self, p):
        return {
            'type': 'SELECT',
            'fields': p.fields,
            'table': p.IDENT,
            'where': p.where_clause,
            'limit': p.limit_clause
        }
    
    @_('WHERE conditions')
    def where_clause(self, p):
        return p.conditions
    
    @_('')
    def where_clause(self, p):
        return None
    
    @_('IDENT EQ STRING')
    def condition(self, p):
        return {'field': p.IDENT, 'op': '=', 'value': p.STRING.strip("'")}
    
    @_('IDENT GT NUMBER')
    def condition(self, p):
        return {'field': p.IDENT, 'op': '>', 'value': float(p.NUMBER)}
    
    @_('LIMIT NUMBER')
    def limit_clause(self, p):
        return int(p.NUMBER)
    
    @_('')
    def limit_clause(self, p):
        return 10

def compile_to_api_call(ast: dict) -> dict:
    """
    Compile AST node to NuroSearch API parameters.
    
    Example:
        SELECT * FROM documents WHERE category = 'sports' AND similarity > 0.82 LIMIT 5
        →
        {
            "endpoint": "/search",
            "params": {"table": "documents", "filter_category": "sports", 
                       "min_similarity": 0.82, "k": 5}
        }
    """
    if ast['type'] == 'SELECT':
        params = {'k': ast.get('limit', 10)}
        
        if ast['where']:
            for condition in ast['where']:
                if condition['field'] == 'category':
                    params['filter_category'] = condition['value']
                elif condition['field'] == 'similarity':
                    params['min_similarity'] = condition['value']
        
        return {"endpoint": "/search", "params": params}
```

### Step 3 — Add `/query` endpoint to Flask

```python
@app.route('/query', methods=['POST'])
def sql_query():
    """Execute a NuroSearch Query Language statement."""
    data = request.json
    query_string = data.get('query', '')
    
    lexer = NuroLexer()
    parser = NuroParser()
    
    try:
        tokens = lexer.tokenize(query_string)
        ast = parser.parse(tokens)
        api_call = compile_to_api_call(ast)
        
        # Execute the compiled API call internally
        results = execute_api_call(api_call)
        
        return jsonify({
            "query": query_string,
            "ast": ast,
            "compiled": api_call,
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e), "query": query_string}), 400
```

## What "Done" Looks Like
- `POST /query` with SQL-like string returns results
- A query console in the frontend lets users type SQL-style queries
- Error messages show which token caused a parse failure
- README shows 5 example queries with outputs

## Resume Impact
**After:** "Built a custom SQL-like query language parser using SLY (Python Lex-Yacc), compiling declarative queries into vector search API calls — demonstrates lexer/parser/AST/query-plan pipeline knowledge"

**Jobs this unlocks:** Database Engineer, Compiler-adjacent roles, Platform Engineer

---

---

# FEATURE 11 — README + Demo GIF (Critical for Visibility)

## What It Is
A well-crafted README is the single highest-ROI thing you can do after building features. Recruiters spend 30 seconds on a GitHub repo. The README is your pitch. The demo GIF is what makes them stay.

## Goal
- Professional README with badges, architecture diagram, benchmark table, and demo GIF
- 30-second screen recording showing: 3D vector map → hybrid search → document upload → RAG answer streaming

## Exact README Structure

```markdown
# NuroSearch 🔍

> Custom Vector Database & RAG Engine — built from scratch, no external DB libraries

[![CI](badge_url)](actions_url) [![codecov](badge_url)](codecov_url) [![Python 3.11](badge)](python)

![Demo GIF](assets/demo.gif)

## What is this?

NuroSearch is a production-architected vector database and RAG pipeline written entirely from scratch in Python. No Pinecone. No LangChain. No Chroma. Every algorithm — HNSW graphs, IVF-PQ compression, BM25 scoring, cross-encoder re-ranking — is implemented from first principles.

**Built for:** developers who want to understand how vector search actually works, not just use it as a black box.

## Benchmark Results

| Algorithm     | Recall@10 | Latency (P99) | QPS    | Memory (10K vecs) |
|---------------|-----------|----------------|--------|-------------------|
| HNSW          | 0.93      | 312 µs         | 4,821  | 2.1 MB            |
| IVF-PQ        | 0.81      | 89 µs          | 12,400 | 0.02 MB           |
| GPU (RTX3060) | 0.93      | 42 µs          | 38,200 | 2.1 MB (VRAM)     |
| Brute Force   | 1.00      | 4,200 µs       | 240    | 2.1 MB            |

*Measured on 10,000 × 768D vectors, Intel i7-12700H, 16GB RAM*

## Features

- **HNSW from scratch** — no FAISS, pure Python graph construction and search
- **IVF-PQ compression** — 99% memory reduction using K-Means + product quantization
- **Hybrid Search** — 70% semantic (vector) + 30% lexical (BM25) weighted fusion
- **Two-stage RAG** — HNSW first-stage recall + cross-encoder neural re-ranking
- **GPU Search** — PyTorch CUDA matrix multiplication, 30x CPU throughput
- **GraphRAG** — Neo4j knowledge graph + vector retrieval for multi-hop reasoning
- **Kafka ingestion** — async document processing pipeline
- **Distributed mode** — 3-node cluster with consistent hashing + Raft consensus
- **3D visualization** — interactive Plotly PCA projection of embedding space
- **CI/CD** — GitHub Actions: lint → tests → benchmark gate → Docker → deploy

## Quick Start

```bash
git clone https://github.com/Prathamesh-Jadhav04/NuroSearch
cd NuroSearch
docker compose up
open http://localhost:8080
```

## Architecture

[architecture diagram image]

## Tech Stack

Python 3.11, Flask, SQLite, Redis, PyTorch, sentence-transformers, Ollama, Neo4j, Apache Kafka, Docker, GitHub Actions

## Author

Prathamesh Jadhav — [GitHub](https://github.com/Prathamesh-Jadhav04) · [LinkedIn](https://linkedin.com/in/prathamesh-jadhav04)
```

## Recording the Demo GIF

Use `OBS Studio` (free) or `Kap` (Mac):
1. Start screen recording, full browser window
2. Show 3D vector map rotating (5 sec)
3. Type a hybrid search query, show results appearing (8 sec)
4. Upload a PDF document (5 sec)
5. Ask a question in "Ask AI", show streaming answer (10 sec)
6. Show benchmark panel with 4 algorithm comparison (5 sec)

Total: ~33 seconds. Save as GIF at 10fps. Compress with `gifsicle` to < 5MB.

---

---

# FEATURE 12 — Unit Tests + pytest Suite

## What It Is
Automated tests that verify every component works correctly and catches regressions. CI fails if tests fail. Shows engineering discipline.

## File Structure

```
tests/
├── __init__.py
├── test_hnsw.py          ← HNSW recall, insert, delete
├── test_bm25.py          ← BM25 scoring, term frequency
├── test_hybrid_search.py ← Hybrid fusion, weighted scoring
├── test_ivfpq.py         ← IVF-PQ encode, recall
├── test_reranker.py      ← Cross-encoder ranking order
├── test_api.py           ← Flask endpoint integration tests
└── benchmark_gate.py     ← CI regression gate (Feature 02)
```

## Key Tests to Write

```python
# tests/test_hnsw.py
def test_hnsw_recall_above_threshold():
    """HNSW must find ≥85% of exact nearest neighbors."""
    index = HNSWIndex(dim=16, M=16, ef_build=200)
    vectors = [random_vector(16) for _ in range(500)]
    for i, v in enumerate(vectors):
        index.insert(i, v)
    
    query = random_vector(16)
    hnsw_results = set(index.search(query, k=10))
    exact_results = set(brute_force_topk(vectors, query, k=10))
    
    recall = len(hnsw_results & exact_results) / 10
    assert recall >= 0.85, f"HNSW recall {recall:.2f} below threshold 0.85"

def test_hnsw_handles_empty_index():
    """Search on empty index must return empty list, not crash."""
    index = HNSWIndex(dim=16)
    results = index.search(random_vector(16), k=5)
    assert results == []

def test_hnsw_insert_and_retrieve_same_vector():
    """Inserting a vector and searching for it should return it as top result."""
    index = HNSWIndex(dim=16)
    v = random_vector(16)
    index.insert(0, v)
    results = index.search(v, k=1)
    assert results[0] == 0  # Same vector should be closest to itself

# tests/test_api.py
def test_stats_endpoint_returns_200(client):
    response = client.get('/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'vector_count' in data
    assert 'algorithms' in data

def test_search_returns_k_results(client):
    # Insert 10 vectors first
    for i in range(10):
        client.post('/insert', json={'id': i, 'embedding': random_vector(16), 'metadata': f'item_{i}'})
    
    v_str = ','.join(str(x) for x in random_vector(16))
    response = client.get(f'/search?v={v_str}&k=5&algo=hnsw&metric=cosine')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['results']) == 5
```

## What "Done" Looks Like
- `pytest tests/ -v` runs all tests in < 30 seconds
- Coverage > 70% (aim for 80%+)
- Codecov badge shows coverage % on README
- All tests pass in CI before any merge to main

---

---

# FEATURE 13 — Technical Blog Post

agent 1 work - 

## What It Is
A public article on Medium or Hashnode titled "How I built a Vector Database from scratch" or "Building HNSW in Python: From theory to benchmark." This is passive discoverability — recruiters find you through Google, not just GitHub.

## Goal
Write a 2000-3000 word technical article covering:
1. What HNSW is and why it's used
2. How you implemented it (code snippets from NuroSearch)
3. Benchmark results with charts
4. Lessons learned and trade-offs

## Outline

```
Title: "I built a Vector Database from scratch — here's what I learned"

1. Introduction (200 words)
   - Why I built this (understand the black box)
   - What I'll cover

2. How HNSW Works (400 words)
   - Hierarchical layers explanation
   - The greedy traversal algorithm
   - Why it's O(log N)

3. Implementation Highlights (600 words)
   - Code snippet: insert() method
   - Code snippet: search() method
   - The tricky parts (entry point, layer assignment)

4. Hybrid Search (300 words)
   - BM25 + vector cosine
   - Weighted fusion formula

5. IVF-PQ Results (300 words)
   - The compression story with before/after numbers
   - Actual benchmark chart image

6. Lessons Learned (300 words)
   - GIL limitations in Python
   - When HNSW beats KD-Tree
   - What I'd do differently

7. GitHub link + call to action
```

## Publish On
- **Medium** → `medium.com` (large audience, searchable)
- **Hashnode** → `hashnode.dev` (developer community, better SEO)
- **Dev.to** → `dev.to` (quick traction)

Cross-post to all three. Link back to GitHub repo in every post.

---

---

## Jobs This Entire Project Unlocks

| Role | Company Types | Which Features Prove Fit |
|------|--------------|--------------------------|
| AI Infrastructure Engineer | Pinecone, Weaviate, Qdrant, Milvus, Zilliz | F01, F06, F08, F02 |
| ML Systems Engineer | Google, Meta, OpenAI, Anthropic | F01, F06, F08, F03 |
| GenAI Engineer | Any startup building RAG products | F03, F07, F09, F04 |
| Applied AI Engineer | Enterprise software companies | F03, F09, F12, F13 |
| MLOps Engineer | Any company with ML pipelines | F04, F05, F07, F12 |
| Backend Engineer (ML-adjacent) | Any tech company | F04, F05, F12, F07 |
| Research Engineer | Labs, universities | F01, F06, F08, F02 |
| Database Engineer | Any DBMS company | F08, F10, F01, F02 |

---

## Final Checklist Before Calling This "Done"

- [ ] F01: `POST /ivfpq/train` works, compression > 90%, benchmark chart updated
- [ ] F02: `python tests/benchmark_gate.py` passes, JSON report generated
- [ ] F03: `/doc/ask?rerank=true` returns rerank_scores in SSE metadata
- [ ] F04: GitHub Actions CI badge is green on README
- [ ] F05: `docker compose up` starts all services in < 60 seconds
- [ ] F06: `/search?algo=gpu` works, benchmark panel shows GPU column
- [ ] F07: `/doc/upload` returns 202 immediately, worker processes async
- [ ] F08: 3-node cluster starts via Docker Compose, search returns `nodes_queried: 3`
- [ ] F09: `/doc/ask/graph` endpoint works, Neo4j browser shows entity graph
- [ ] F10: `POST /query` with SQL string returns results
- [ ] F11: README has demo GIF, badge, benchmark table, one-command startup
- [ ] F12: `pytest tests/ -v` passes, coverage > 70%
- [ ] F13: Blog post published and linked from README

---

*This AGENT.md was generated for Prathamesh Jadhav (Prathamesh-Jadhav04) as a complete implementation guide for NuroSearch. Every feature here was discussed, prioritized, and ordered based on resume impact, implementation difficulty, and job market fit as of 2025-2026.*