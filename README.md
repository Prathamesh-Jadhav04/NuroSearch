# NuroSearch — Custom Vector Database with RAG Pipeline

A production-grade **Vector Database** built from scratch in Python with a premium monochrome web UI. Implements **HNSW**, **KD-Tree**, and **Brute Force** search algorithms with a complete **RAG (Retrieval-Augmented Generation)** pipeline powered by local LLMs via Ollama.

> **Built to demonstrate deep understanding of vector search, semantic retrieval, and LLM integration — from algorithm implementation to production-ready API.**

---

## 🚀 Key Highlights

| Metric | Detail |
|---|---|
| **Search Algorithms** | HNSW, KD-Tree, Brute Force — implemented from scratch |
| **Distance Metrics** | Cosine Similarity, Euclidean, Manhattan |
| **Hybrid Search** | BM25 (lexical) + Vector (semantic) combined retrieval |
| **RAG Pipeline** | Document chunking → Embedding → HNSW retrieval → LLM answer |
| **Performance** | O(log N) search complexity via HNSW multilayer graph |
| **Persistence** | SQLite with WAL journaling for crash-safe storage |
| **API** | Full REST API with CRUD, benchmark, and SSE streaming |
| **Visualization** | Real-time 2D/3D PCA projection of semantic vector space |

---

## 🛠 Tech Stack

**Backend:** Python 3.9+, Flask, SQLite, Redis (optional caching)  
**Algorithms:** HNSW (from scratch), KD-Tree (from scratch), Brute Force, BM25  
**AI/ML:** Ollama (nomic-embed-text, qwen2.5), PCA dimensionality reduction  
**Frontend:** HTML5, CSS3, Vanilla JS, Plotly.js (3D visualization)  
**Architecture:** REST API, Server-Sent Events (SSE), Chunk-based document processing  

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        NuroSearch                           │
├─────────────────────────────────────────────────────────────┤
│  Frontend (index.html)                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ Search UI    │  │ 3D Viz       │  │ RAG Chat          │ │
│  │ + Benchmark  │  │ (Plotly.js)  │  │ + SSE Streaming   │ │
│  └──────────────┘  └──────────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Backend (main.py)                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ VectorDB     │  │ DocumentDB   │  │ OllamaClient      │ │
│  │ HNSW/KD/BF   │  │ 768D Index   │  │ Embed + Generate  │ │
│  └──────────────┘  └──────────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Storage: SQLite (vectors.db) + Redis Cache (optional)      │
└─────────────────────────────────────────────────────────────┘
```

### RAG Pipeline Flow

```
User Question
    │
    ▼
┌─────────────────────┐
│ Query Embedding     │  nomic-embed-text → 768D vector
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ HNSW Vector Search  │  O(log N) — finds top-k chunks
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Context Assembly    │  Retrieved chunks → prompt context
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ LLM Generation      │  qwen2.5:0.5b → streamed answer
└─────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites

1. **Python 3.9+**
2. **Ollama** — https://ollama.com

### Setup

```bash
# 1. Pull AI models
ollama pull nomic-embed-text    # Embedding model (~274 MB)
ollama pull qwen2.5:0.5b        # Generation model (~390 MB)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run server
python main.py

# 4. Open browser
http://localhost:8080
```

---

## 🎯 Features

### 1. Multi-Algorithm Vector Search

Three search algorithms implemented from scratch, selectable at runtime:

| Algorithm | Complexity | Type | Best For |
|---|---|---|---|
| **HNSW** | O(log N) | Approximate | High-dimensional vectors (768D) |
| **KD-Tree** | O(log N) | Exact | Low-dimensional vectors (≤20D) |
| **Brute Force** | O(N·d) | Exact | Baseline comparison, small datasets |
| **Hybrid** | O(N·d) + BM25 | Combined | Best accuracy (semantic + lexical) |

### 2. Real-Time Visualization

- **3D PCA Scatter Plot** — Interactive Plotly visualization showing semantic clusters
- **2D Vector Space Graph** — Live query visualization with match highlighting
- **HNSW Graph Structure** — Layer-by-layer node distribution view
- **Performance Benchmark** — Side-by-side algorithm speed comparison

### 3. Document RAG Pipeline

- **Text Embedding** — Paste text or upload PDF/TXT files
- **Auto Chunking** — Documents split into overlapping 250-word chunks
- **Semantic Retrieval** — HNSW finds most relevant context chunks
- **LLM Answer** — Local LLM generates answers from retrieved context only
- **SSE Streaming** — Real-time typewriter effect for answers

### 4. REST API

Full CRUD API with 13+ endpoints for programmatic access:

```bash
# Search
GET /search?v=0.9,0.8,...&k=5&metric=cosine&algo=hnsw

# Insert vector
POST /insert {"metadata":"...","category":"...","embedding":[...]}

# Benchmark all algorithms
GET /benchmark?v=...&k=5&metric=cosine

# RAG: Ask AI
POST /doc/ask {"question":"...","k":3}

# SSE streaming response
```

---

## 📊 Algorithm Deep Dive

### HNSW (Hierarchical Navigable Small World)

Built a multilayer graph from scratch where:
- **Layer 0** contains all nodes with dense connections
- **Higher layers** are exponentially sparser (highway layers)
- **Search** starts at top layer, greedily descends to layer 0
- **Insert** uses beam search (ef_construction=200) for optimal connections

**Why HNSW:** Same algorithm used by Pinecone, Weaviate, Chroma, Milvus. Achieves O(log N) search in high-dimensional spaces where KD-Trees fail.

### KD-Tree (K-Dimensional Tree)

Binary space partitioning with:
- **Axis-aligned splits** cycling through all dimensions
- **Ball-within-hyperslab pruning** for efficient search
- **Optimal for ≤20D** — degrades to O(N) at 768D (curse of dimensionality)

### Hybrid Search (BM25 + Vector)

Combines lexical and semantic retrieval:
- **BM25** scores keyword relevance
- **Cosine similarity** scores semantic relevance
- **Weighted fusion** produces combined ranking

---

## 🏗 Project Structure

```
NuroSearch/
├── main.py              ← Flask backend (42KB)
│   ├── HNSW             ← Hierarchical Navigable Small World (from scratch)
│   ├── KDTree           ← K-Dimensional Tree (from scratch)
│   ├── BruteForce       ← O(N·d) baseline
│   ├── BM25             ← Lexical search scoring
│   ├── VectorDB         ← Unified 16D demo vector interface
│   ├── DocumentDB       ← 768D Ollama embedding index
│   ├── OllamaClient     ← HTTP client for embedding + generation
│   ├── SQLiteDB         ← SQLite persistence with WAL journaling
│   └── REST API         ← 13+ endpoints with SSE streaming
├── index.html           ← Frontend (88KB)
│   ├── Search UI        ← Algorithm/metric selection, results
│   ├── 3D Viz           ← Plotly.js PCA scatter plot
│   ├── Pipeline Viz     ← Live RAG pipeline visualization
│   ├── Chat UI          ← RAG Q&A with streaming
│   └── Benchmark        ← Algorithm performance comparison
├── requirements.txt     ← Python dependencies
├── .gitignore           ← Git ignore rules
└── README.md            ← This file
```

---

## 💡 Key Technical Decisions

| Decision | Rationale |
|---|---|
| **HNSW from scratch** | Demonstrates understanding of production vector search internals |
| **Multiple algorithms** | Shows trade-off analysis (speed vs accuracy vs dimensionality) |
| **Local LLMs (Ollama)** | Privacy-first, no API costs, works offline |
| **SQLite + WAL** | Crash-safe persistence without external dependencies |
| **SSE streaming** | Better UX for LLM responses vs polling |
| **PCA visualization** | Makes abstract vector space concepts tangible |

---

## 📈 Performance Characteristics

| Operation | HNSW | KD-Tree | Brute Force |
|---|---|---|---|
| **Search (16D)** | ~50μs | ~30μs | ~200μs |
| **Search (768D)** | ~500μs | ~O(N) | ~2ms |
| **Insert** | ~1ms | ~0.5ms | ~0.1ms |
| **Memory** | O(N·M) | O(N) | O(N) |

*Measured on laptop CPU. Actual values vary with dataset size.*

---

## 🔧 API Reference

### Vector Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/search?v=...&k=5&metric=cosine&algo=hnsw` | K-NN search |
| `POST` | `/insert` | Insert demo vector |
| `DELETE` | `/delete/:id` | Delete vector |
| `GET` | `/items` | List all vectors |
| `GET` | `/benchmark?v=...&k=5` | Compare all algorithms |
| `GET` | `/hnsw-info` | HNSW graph structure |
| `GET` | `/stats` | Database statistics |

### Document & RAG Endpoints

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `POST` | `/doc/insert` | `{"title":"...","text":"..."}` | Embed document |
| `POST` | `/doc/upload` | multipart form | Upload PDF/TXT |
| `GET` | `/doc/list` | — | List documents |
| `DELETE` | `/doc/delete/:id` | — | Delete document |
| `POST` | `/doc/ask` | `{"question":"...","k":3}` | RAG query (SSE) |
| `GET` | `/status` | — | Ollama status |

---

## 🎓 What This Project Demonstrates

### For Resume / Interviews

- **Algorithm Implementation:** Built HNSW and KD-Tree from scratch — not just library usage
- **Systems Design:** Multi-component architecture (search, storage, AI, API, UI)
- **Performance Optimization:** O(log N) search, WAL journaling, Redis caching
- **ML/AI Integration:** Embedding models, RAG pipeline, prompt engineering
- **Full-Stack Development:** Backend (Python/Flask) + Frontend (HTML/CSS/JS/Plotly)
- **API Design:** RESTful endpoints, SSE streaming, error handling
- **Data Structures:** Graph algorithms, tree structures, vector spaces, PCA

### Skills Showcased

```
Python · Flask · REST API · SQLite · Redis
HNSW · KD-Tree · BM25 · PCA · Vector Search
RAG · LLM Integration · Ollama · SSE
HTML/CSS/JS · Plotly.js · Data Visualization
Algorithm Design · Performance Optimization · Systems Architecture
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|---|---|
| `Ollama: OFFLINE` | Run `ollama serve` in terminal |
| First embed is slow | Ollama downloading model — wait 2 min |
| Port 8080 in use | `netstat -ano | findstr 8080` then `taskkill /PID <pid> /F` |
| LLM answer slow | Normal — qwen2.5:0.5b takes 5-15s on CPU |

### Use Different LLM

```bash
ollama pull llama3.2
# Edit main.py: self.gen_model = "llama3.2"
# Restart server
```

---

## 📄 License

MIT — use this however you want.

---

## 👤 Author

**Prathamesh Jadhav**  
- 📧 Prathamesh.jadhav.office@gmail.com
- 🔗 [LinkedIn](https://www.linkedin.com/in/prathamesh-jadhav04)
- 🐙 [GitHub](https://github.com/Prathamesh-Jadhav04)
