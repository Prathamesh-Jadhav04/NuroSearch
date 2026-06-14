---
title: NuroSearch
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

<!-- Badges -->
[![CI/CD](https://github.com/Prathamesh-Jadhav04/NuroSearch/actions/workflows/ci.yml/badge.svg)](https://github.com/Prathamesh-Jadhav04/NuroSearch/actions) [![codecov](https://codecov.io/gh/Prathamesh-Jadhav04/NuroSearch/branch/main/graph/badge.svg)](https://codecov.io/gh/Prathamesh-Jadhav04/NuroSearch) [![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/) [![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker)](https://ghcr.io/prathamesh-jadhav04/nurosearch) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

# 🔍 NuroSearch

**A production-grade vector database and RAG engine built from scratch — no Pinecone, no Weaviate, no shortcuts.**

---

<!-- Live Demo -->
<p align="center">
  <a href="https://huggingface.co/spaces/Prathamesh-Jadhav04/NuroSearch">
    <img src="https://img.shields.io/badge/🚀%20Live%20Demo-HuggingFace%20Spaces-FFD21E?style=for-the-badge&logo=huggingface&logoColor=000" alt="Live Demo"/>
  </a>
</p>

<p align="center">
  <b>👉 <a href="https://huggingface.co/spaces/Prathamesh-Jadhav04/NuroSearch">Try NuroSearch live — no setup needed</a> 👈</b>
</p>

---

## 💡 What Is This / Why I Built This

Every vector database today is a black box. You `pip install` it, call an API, and pray the recall numbers are real. I wanted to understand what actually happens when you search a million vectors in under 7 milliseconds — so I built it myself.

**NuroSearch** is a full-stack vector search engine written from the ground up in Python. It implements HNSW graph traversal, IVF-PQ compression, BM25 lexical scoring, GPU-accelerated brute-force via PyTorch, and a Raft-based distributed cluster — all wired together behind a Flask REST API with a single-command Docker deployment. It is not a wrapper around FAISS or Annoy. Every algorithm, every data structure, every optimization is hand-written and benchmarked. The project doubles as a complete RAG pipeline: upload PDFs, auto-chunk, embed with Ollama, search with hybrid ranking, re-rank with a cross-encoder, and answer questions with LLM-generated responses enriched by a Neo4j knowledge graph.

---

## 📊 Benchmark Results

Measured on 1,000 vectors × 100 queries (16-D, cosine distance, HNSW M=16, ef=200):

| Metric | Value |
|---|---|
| **Recall@10** | **1.00** (100%) |
| **QPS** | **147** queries/sec |
| **Mean Latency** | **6.7 ms** |
| **P99 Latency** | **14.1 ms** |
| **IVF-PQ Compression** | **96×** (768-D float32 → 8 bytes) |
| **GPU Speedup (CUDA)** | **~500×** vs Python loops |
| **Benchmark Gate** | ✅ Pass (threshold ≥ 0.85) |

> Benchmarks are reproducible — run `POST /benchmark/run` or execute `python tests/benchmark_gate.py`. Reports auto-upload as CI artifacts on every commit.

---

## ✨ Features

- **HNSW Graph Index** — Hierarchical Navigable Small World graph with configurable `M`, `ef_build`, and multi-layer traversal for sub-linear approximate nearest neighbor search
- **IVF-PQ Compression** — Inverted File Index with Product Quantization compresses 768-D float vectors into 8-byte codes (96× memory reduction) using MiniBatchKMeans codebook training and Asymmetric Distance Computation (ADC)
- **GPU-Accelerated Search (PyTorch)** — Batched cosine similarity via `torch.mm` matrix multiplication on CUDA; falls back to CPU tensors (~3× faster than NumPy) when no GPU is available
- **Hybrid Search (BM25 + Vector)** — Reciprocal Rank Fusion merges sparse BM25 lexical scores with dense vector similarity for combined keyword-and-semantic retrieval
- **Cross-Encoder Re-Ranking** — Two-stage retrieval pipeline: HNSW retrieves top-N candidates fast, then `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranks them precisely for maximum relevance
- **Distributed Cluster (Raft Consensus)** — 3-node worker cluster with PySyncObj Raft replication, consistent hash-based sharding via coordinator, and scatter-gather search across all shards
- **Async Document Ingestion (Kafka)** — Upload PDFs or text → Kafka produces ingestion events → worker processes chunk, embed (Ollama `nomic-embed-text`), and index asynchronously with real-time status tracking
- **GraphRAG (Neo4j Knowledge Graph)** — LLM-extracted entity-relationship triples stored in Neo4j; multi-hop graph traversal enriches RAG context for deeper, more factual answers
- **SQL-like Query Language** — Custom lexer/parser (SLY) supports `SELECT * FROM documents WHERE category = 'sports' AND similarity > 0.82 LIMIT 5` compiled to API calls
- **Full CI/CD Pipeline** — GitHub Actions: Ruff lint → Black format → Mypy types → Bandit security → Pytest + Codecov → Benchmark gate → Docker build/push to GHCR → SSH deploy

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client (Browser / cURL)                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Flask REST API (main.py :7860)                   │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Search   │ │  Insert   │ │ Doc/Ask  │ │ Doc/Upload│ │Benchmark │ │
│  │ Endpoint  │ │ Endpoint  │ │  (RAG)   │ │  (PDF)   │ │  Gate    │ │
│  └─────┬─────┘ └─────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────┘ │
└────────┼─────────────┼────────────┼────────────┼────────────────────┘
         │             │            │            │
    ┌────▼────┐   ┌────▼────┐  ┌───▼───┐   ┌───▼────┐
    │  HNSW   │   │ IVF-PQ  │  │Ollama │   │ Kafka  │
    │  Index  │   │  Index  │  │ LLM   │   │Producer│
    │(in-mem) │   │(trained)│  │Embed +│   │        │
    └─────────┘   └─────────┘  │  Gen  │   └───┬────┘
    ┌─────────┐   ┌─────────┐  └───┬───┘       │
    │ BM25    │   │  GPU    │      │        ┌──▼──────────┐
    │(lexical)│   │ Search  │      │        │  Ingestion  │
    └─────────┘   │(PyTorch)│      │        │   Worker    │
                  └─────────┘      │        └─────────────┘
                              ┌────▼────┐
    ┌─────────┐               │Cross-Enc│   ┌─────────────┐
    │ SQLite  │               │Reranker │   │   Neo4j     │
    │  (DB)   │               └─────────┘   │ Knowledge   │
    └─────────┘                             │   Graph     │
    ┌─────────┐                             └─────────────┘
    │  Redis  │
    │ (Cache) │
    └─────────┘

    ┌───────────────── Distributed Cluster ──────────────────┐
    │                                                        │
    │  ┌─────────────┐                                       │
    │  │ Coordinator │──── Consistent Hash Routing           │
    │  │   (:8090)   │                                       │
    │  └──────┬──────┘                                       │
    │         │  Scatter-Gather                              │
    │   ┌─────┼─────┐                                       │
    │   ▼     ▼     ▼                                       │
    │ Worker Worker Worker   ← Raft Consensus (PySyncObj)   │
    │ :8081  :8082  :8083                                    │
    └────────────────────────────────────────────────────────┘
```

The architecture follows a modular design where each component degrades gracefully — Redis, Kafka, Neo4j, GPU, and Ollama are all optional. The system runs in full single-node mode or scales to a 3-node Raft-replicated cluster with scatter-gather search.

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Prathamesh-Jadhav04/NuroSearch.git
cd NuroSearch

# Start with Docker Compose (includes Redis + app)
docker compose up -d

# Open the dashboard
open http://localhost:8080

# Seed sample data (optional)
python seed_dummy_data.py

# Run with Kafka + distributed cluster (optional profiles)
docker compose --profile kafka --profile cluster up -d
```

> **Prerequisites:** Docker & Docker Compose. Ollama is bundled inside the Docker image with pre-downloaded `nomic-embed-text` and `qwen2.5:0.5b` models — no extra setup needed.

---

## 📖 API Reference

### Vector Operations

| Method | Endpoint | Description | Key Parameters |
|--------|----------|-------------|----------------|
| `GET` | `/search` | K-nearest neighbor vector search | `v` (comma-sep vector), `k`, `algo` (hnsw/bf/kdtree/ivfpq/gpu), `metric` (cosine/euclidean/manhattan) |
| `POST` | `/insert` | Insert a vector with metadata | `emb` (vector array), `meta` (string), `cat` (category) |
| `DELETE` | `/delete/<id>` | Remove a vector by ID | Path param: `id` |
| `GET` | `/items` | List all indexed vectors | — |
| `GET` | `/stats` | Index statistics and memory usage | — |

### Document / RAG Operations

| Method | Endpoint | Description | Key Parameters |
|--------|----------|-------------|----------------|
| `POST` | `/doc/insert` | Insert a text document (auto-embeds via Ollama) | `title`, `text` |
| `POST` | `/doc/upload` | Upload a PDF or text file | `file` (multipart), `async` (boolean) |
| `POST` | `/doc/search` | Semantic search across documents | `query`, `k`, `rerank` (boolean) |
| `POST` | `/doc/ask` | RAG question answering with LLM | `question`, `k`, `rerank`, `model` |
| `POST` | `/doc/ask/graph` | GraphRAG with Neo4j knowledge graph context | `question`, `k`, `hops` |
| `GET` | `/doc/list` | List all indexed documents | — |
| `GET` | `/doc/status/<id>` | Check async ingestion status | Path param: `doc_id` |

### System & Benchmarking

| Method | Endpoint | Description | Key Parameters |
|--------|----------|-------------|----------------|
| `POST` | `/benchmark/run` | Execute benchmark suite | — |
| `GET` | `/benchmark/report` | Retrieve latest benchmark JSON | — |
| `POST` | `/ivfpq/train` | Train IVF-PQ codebooks on current data | — |
| `GET` | `/ivfpq/stats` | IVF-PQ compression statistics | — |
| `POST` | `/query` | Execute NuroSearch SQL-like query | `query` (NQL string) |
| `GET` | `/status` | System-wide health and component status | — |

---

## 📁 Project Structure

```
nurosearch/
├── main.py                 # Flask app — all API endpoints, index management, RAG pipeline
├── hnsw.py                 # HNSW graph index (from-scratch implementation)
├── ivfpq.py                # IVF-PQ index with MiniBatchKMeans codebook training
├── gpu_search.py           # PyTorch GPU/CPU accelerated brute-force search
├── reranker.py             # Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2)
├── query_parser.py         # SQL-like NuroSearch Query Language (SLY lexer/parser)
├── knowledge_graph.py      # Neo4j GraphRAG — triple extraction & multi-hop traversal
├── coordinator.py          # Distributed coordinator — consistent hashing, scatter-gather
├── worker.py               # Distributed worker node — HNSW shard + Raft replication
├── ingestion_worker.py     # Kafka consumer — async document chunking & embedding
├── kd_tree.py              # KD-Tree index (alternative spatial index)
├── seed_dummy_data.py      # Sample data seeder for demos
├── index.html              # Full-featured web dashboard (single-file SPA)
├── start.sh                # Entrypoint — starts Ollama, workers, coordinator, Gunicorn
├── Dockerfile              # Multi-stage build with bundled Ollama + models
├── docker-compose.yml      # Full stack — app, Redis, Kafka (profile), cluster (profile)
├── requirements.txt        # Pinned dependencies with version ranges
├── .env.example            # Environment variable template
├── test_features.py        # Feature integration tests
├── tests/
│   ├── benchmark_gate.py   # CI benchmark gate (recall@10 ≥ 0.85 or fail)
│   ├── test_hnsw.py        # HNSW unit tests
│   ├── test_ivfpq.py       # IVF-PQ unit tests
│   ├── test_gpu.py         # GPU search tests
│   ├── test_bm25.py        # BM25 scoring tests
│   ├── test_hybrid_search.py # Hybrid search tests
│   ├── test_parser.py      # Query parser tests
│   ├── test_reranker.py    # Cross-encoder reranker tests
│   ├── test_graph.py       # Knowledge graph tests
│   ├── test_distributed.py # Distributed cluster tests
│   ├── test_kafka_ingestion.py # Kafka ingestion tests
│   └── test_api.py         # API endpoint integration tests
└── .github/
    └── workflows/
        └── ci.yml          # 5-stage CI/CD: lint → test → benchmark → docker → deploy
```

---

## ⚠️ Known Limitations

- **Ghost Shards on Node Failure** — If a worker node crashes mid-write before Raft consensus commits, the coordinator's consistent hash may still route reads to that shard, returning stale or empty results until the node recovers and replays the Raft log
- **Single-Threaded IVF-PQ Training** — The `MiniBatchKMeans` codebook training in `ivfpq.py` runs synchronously on a single core; training on >100K vectors can block the Flask event loop for several seconds without background offloading
- **No Persistent HNSW Serialization** — The in-memory HNSW graph is rebuilt from SQLite on every cold start; there is no mmap or binary snapshot, so boot time scales linearly with index size
- **Kafka and Neo4j Are Optional Singletons** — Both Kafka ingestion and Neo4j graph enrichment use single-instance connections without connection pooling or automatic reconnect, which can cause silent failures under sustained load

---

## 🗺️ Roadmap

- [ ] **HNSW Binary Snapshots** — Serialize the graph to disk with mmap-backed reads for instant cold starts
- [ ] **SIMD Distance Kernels** — Replace NumPy distance functions with AVX-512/NEON intrinsics via Cython for 4-8× throughput on CPU
- [ ] **Multi-Tenant Namespaces** — Isolate indexes per tenant with separate HNSW graphs and access control
- [ ] **Streaming Incremental IVF-PQ** — Online codebook updates without full retraining when new vectors arrive
- [ ] **Prometheus + Grafana Observability** — Export QPS, latency percentiles, cache hit rates, and Raft replication lag as Prometheus metrics

---

## 👤 Author & Connect

**Prathamesh Jadhav** — Built every line of this project from scratch.

[![GitHub](https://img.shields.io/badge/GitHub-Prathamesh--Jadhav04-181717?logo=github)](https://github.com/Prathamesh-Jadhav04)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-prathameshjadhav04-0A66C2?logo=linkedin)](https://linkedin.com/in/prathameshjadhav04)
[![Email](https://img.shields.io/badge/Email-prathameshjadhav4004@gmail.com-EA4335?logo=gmail)](mailto:prathameshjadhav4004@gmail.com)

---

<p align="center">
  <i>If you found this useful, consider giving it a ⭐ on <a href="https://github.com/Prathamesh-Jadhav04/NuroSearch">GitHub</a>.</i>
</p>
