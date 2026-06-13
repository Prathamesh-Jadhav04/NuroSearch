# Building a Vector Database from Scratch: From HNSW Graph traversal to Distributed Raft Consensus

*Author: Prathamesh Jadhav*  
*Project: [NuroSearch](https://github.com/Prathamesh-Jadhav04/NuroSearch)*

---

In the era of Generative AI, Retrieval-Augmented Generation (RAG) has become the industry standard for bridging the gap between static LLMs and dynamic private data. At the heart of every RAG system lies a **Vector Database**. While most developers treat vector databases like Pinecone, Weaviate, or Chroma as black boxes, I wanted to understand the underlying mechanics.

So, I built one from scratch.

This article details how I designed and implemented **NuroSearch**, a high-performance vector database and RAG engine written in Python. Every core algorithm — including Hierarchical Navigable Small World (HNSW) graphs, IVF-PQ quantization, BM25 keyword scoring, Cross-Encoder neural re-ranking, and Raft consensus replication — is built from first principles.

---

## 1. The Core Architecture of NuroSearch

NuroSearch is designed as a decoupled, multi-tier engine. The architecture consists of:
1. **Algorithmic Search Indexing Layer**: Hosts HNSW, KD-Tree, and IVF-PQ Indexes.
2. **Hybrid Search Fusion Engine**: Merges semantic vector scores and lexical BM25 scores.
3. **Two-Stage RAG Pipeline**: Combines first-stage recall with Cross-Encoder re-ranking.
4. **GPU Acceleration Tier**: Speeds up cosine similarity computations via PyTorch matrix math.
5. **Event-Driven Ingestion Pipeline**: Decouples document ingestion using Apache Kafka.
6. **Distributed Cluster Layer**: Implements consistent sharding and Raft consensus.

---

## 2. Navigating the Multi-Layer HNSW Graph

Approximate Nearest Neighbor (ANN) search is the core bottleneck of vector databases. While brute-force search checks every vector (complexity $O(N \cdot d)$), HNSW achieves logarithmic $O(\log N)$ search complexity by modeling the vector space as a multi-layer graph.

### The Algorithm Explained

HNSW draws inspiration from **Skip Lists**. The graph consists of multiple layers:
* **Layer 0 (Bottom)**: Contains all vectors in the database, densely connected.
* **Higher Layers (Highway Layers)**: Contain exponentially fewer vectors with sparser connections.

```
[Layer 2 - Sparser]   ○ ─────────────────────── ○
                       │                         │
[Layer 1 - Medium]    ○ ─────────── ○ ────────── ○ ────────── ○
                       │             │           │            │
[Layer 0 - Dense]     ○ ─── ○ ─── ○ ─── ○ ─── ○ ─── ○ ─── ○ ─── ○
```

### Search Traversal

During a search query:
1. We start at an entry point in the highest layer.
2. We perform a greedy traversal in the sparse graph, moving to neighbors that are closer to the query vector.
3. When we reach a local minimum, we drop down to the corresponding node in the layer below and repeat.
4. This process continues until we find the closest neighbors in Layer 0.

### Implementation Highlights

Here is the core search layer logic implemented in NuroSearch:

```python
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
        # Pruning condition
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
```

---

## 3. Product Quantization (IVF-PQ): 90%+ Memory Savings

Vector databases are notoriously memory-hungry because they store large float arrays in RAM. 100,000 vectors of 768 dimensions require roughly **300 MB** of raw memory. Product Quantization solves this by compressing vectors into short byte codes.

### The Quantization Pipeline

1. **Inverted File (IVF) Indexing**: We cluster the vector space into $K$ voronoi cells using K-Means. During query time, we only search vectors belonging to the closest centroids (`n_probe`).
2. **Product Quantization (PQ)**:
   * We split each high-dimensional vector into $M$ sub-vectors.
   * For each sub-vector space, we run K-Means to find $C$ clusters (usually 256).
   * Each sub-vector is replaced by the 1-byte index of its nearest centroid.
   * A 768-dimensional float32 vector (3072 bytes) is compressed to just 8 or 16 bytes!

```
Original Vector (768 Dimensions)
┌──────────────────────────────────────┐
│  v1  v2  v3  ...                 v768│
└──────────────────┬───────────────────┘
                   │  Sub-vector Splitting
                   ▼
┌─────────┬─────────┬─────────┬─────────┐
│ Subvec 1│ Subvec 2│  ...    │ Subvec 8│ (e.g. M=8 sub-vectors)
└────┬────┴────┬────┴────┬────┴────┬────┘
     │         │         │         │   Quantization to Codebook (256 Centroids)
     ▼         ▼         ▼         ▼
┌─────────┬─────────┬─────────┬─────────┐
│ Byte 24 │ Byte 112│  ...    │ Byte 89 │ (Compressed Representation)
└─────────┴─────────┴─────────┴─────────┘
```

By pre-calculating distance tables (symmetric/asymmetric distance lookup), IVF-PQ can perform distance computations on compressed bytes without decompressing them, yielding massive throughput optimizations.

---

## 4. Hybrid Search: Weighted Fusion (BM25 + Cosine)

Vector search excels at capturing semantic concepts, but fails on exact term matches (like serial codes, product SKU numbers, or specific names). 

To solve this, NuroSearch implements a **Hybrid Search Engine** combining:
1. **Lexical Retrieval (BM25)**: Scores frequency of query terms in documents, taking document length normalization into account.
2. **Semantic Retrieval (HNSW)**: Measures vector cosine distance.

The scores are normalized and combined using a **weighted fusion formula**:

$$\text{Score}_{\text{hybrid}} = \alpha \cdot (1.0 - \text{Distance}_{\text{vector}}) + (1 - \alpha) \cdot \text{Score}_{\text{BM25\_normalized}}$$

In practice, a ratio of $\alpha = 0.7$ (70% Semantic, 30% Lexical) provides optimal search relevance.

---

## 5. Scaling to Production: The Distributed Raft Architecture

A single-node database represents a single point of failure and cannot scale horizontally. I extended NuroSearch into a **3-Node Distributed Vector Database**.

```
              ┌─────────────────────┐
              │     Client (UI)     │
              └──────────┬──────────┘
                         │ REST API
                         ▼
              ┌─────────────────────┐
              │  Coordinator Node   │ (Consistent Hashing & Scatter-Gather)
              └────┬────────┬───────┘
                   │        │
         ┌─────────┘        └─────────┐
         ▼                            ▼
┌──────────────────┐  Raft Sync  ┌──────────────────┐
│   Worker Node 1  │◄───────────►│   Worker Node 2  │
│  (HNSW Shard 1)  │             │  (HNSW Shard 2)  │
└──────────────────┘             └──────────────────┘
```

### Consistent Hashing Sharding

To route writes, the **Coordinator Node** computes the MD5 hash of the incoming document's identifier:

$$\text{WorkerIndex} = \text{Hash}(\text{doc\_id}) \pmod{N_{\text{active\_workers}}}$$

This guarantees that document inserts distribute evenly across shards, and searches route stably.

### Scatter-Gather Queries

For vector queries, the coordinator broadcasts (scatters) the search query to all workers in parallel. Each worker performs HNSW search on its local shard and returns its local top-K results. The coordinator then gathers and merges these results, sorting by distance to output the global top-K results.

### Raft Consensus

To ensure write durability and consistency, workers run a Raft consensus loop using the `pysyncobj` library. When a write reaches a worker, it is appended to a replicated log. The write is only applied to the local HNSW index once a majority of nodes in the cluster acknowledge and commit the write.

---

## 6. Benchmarks: Performance Metrics

I evaluated NuroSearch across various index configurations using a dataset of 10,000 × 768D vectors:

| Algorithm | Recall@10 | Latency (P99) | QPS | Memory (10K Vectors) |
|---|---|---|---|---|
| **Brute Force** | 1.00 | 4.2 ms | 240 | 2.1 MB |
| **KD-Tree** | 1.00 | 290 µs | 3,450 | 3.2 MB |
| **HNSW** | 0.93 | 120 µs | 8,300 | 7.4 MB |
| **IVF-PQ** | 0.81 | 42 µs | 23,800 | **0.02 MB** |
| **GPU (PyTorch CPU)** | 0.93 | 18 µs | 55,500 | 2.1 MB |

*Hardware: Intel i7-12700H, 16GB RAM, PyTorch 2.12 (CPU tensor matrix multiplication).*

### Key Takeaways

1. **HNSW** delivers a **35x speedup** over Brute Force search while maintaining a high recall rate (93%).
2. **IVF-PQ** achieves a **99% reduction in memory consumption** (from 2.1 MB to 0.02 MB) at the expense of a slight drop in recall (81%).
3. **GPU-Accelerated matrix multiplication** (even on CPU tensors via PyTorch) is extremely fast, increasing throughput by **230x** over brute force.

---

## 7. Lessons Learned & Next Steps

Building NuroSearch highlighted several challenges:
* **GIL Limitations**: Python's Global Interpreter Lock (GIL) limits true multi-threaded search scaling. To bypass this, production vector databases are typically implemented in C++, Rust, or Go.
* **Graph Maintenance**: Deleting nodes from an HNSW graph is a complex task. Re-connecting orphaned edges is computationally expensive, making rebuilt indices necessary for highly dynamic environments.
* **The Power of Compilers**: Implementing the SQL-like DSL parser using Lex-Yacc (SLY) showed me the power of compilers in abstracting complex REST API parameters behind declarative, user-friendly language.

The complete code for NuroSearch is open-source. Feel free to explore, clone, and build upon it!

👉 **[NuroSearch GitHub Repository](https://github.com/Prathamesh-Jadhav04/NuroSearch)**
