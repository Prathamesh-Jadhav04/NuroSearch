# NuroSearch: Features & Cluster Testing Guide

This guide provides an overview of the NuroSearch system components, their use cases, and step-by-step instructions to test all features with concrete demo data.

---

## 1. Project Components & Their Uses

NuroSearch is a high-performance hybrid (lexical + semantic) sharded vector database with GraphRAG, SQL-like DSL query compiler, and GPU acceleration. Here are the core files and what they do:

### Core Files
*   **`main.py`** [main.py](file:///D:/My%20Own%20Artificial%20Intelligance/main.py): The main gateway and frontend API server. It serves the Web UI (`index.html`), handles basic search algorithms (HNSW, KD-Tree, Brute Force), coordinates RAG queries (Ollama), runs IVF-PQ quantization, performs 3D PCA dimension reduction, and manages local SQLite persistence (`vectors.db`).
*   **`index.html`** [index.html](file:///D:/My%20Own%20Artificial%20Intelligance/index.html): The premium front-end dashboard featuring the interactive 3D semantic canvas, SQL query console, RAG chat box, AI pipeline visualization, and the real-time Cluster Monitor.
*   **`hnsw.py`** [hnsw.py](file:///D:/My%20Own%20Artificial%20Intelligance/hnsw.py): A custom from-scratch implementation of Hierarchical Navigable Small World (HNSW) graphs for fast vector search.
*   **`ivfpq.py`** [ivfpq.py](file:///D:/My%20Own%20Artificial%20Intelligance/ivfpq.py): Inverted File Product Quantization (IVF-PQ) engine which compresses high-dimensional vectors to save up to 99% of memory.

### Advanced Features (Features 06 - 10)
*   **`gpu_search.py`** [gpu_search.py](file:///D:/My%20Own%20Artificial%20Intelligance/gpu_search.py) (Feature 06): PyTorch-based GPU vector search index that leverages CUDA to process millions of similarity matches instantly (falls back gracefully to CPU if GPU is unavailable).
*   **`ingestion_worker.py`** [ingestion_worker.py](file:///D:/My%20Own%20Artificial%20Intelligance/ingestion_worker.py) (Feature 07): Kafka consumer node that listens for asynchronous document uploads, chunks and embeds them, and updates Redis cache status.
*   **`worker.py`** [worker.py](file:///D:/My%20Own%20Artificial%20Intelligance/worker.py) (Feature 08): Cluster Worker. Runs a shard of the vector database. Uses **Raft Consensus** (`pysyncobj`) to replicate operations across worker replicas.
*   **`coordinator.py`** [coordinator.py](file:///D:/My%20Own%20Artificial%20Intelligance/coordinator.py) (Feature 08): Cluster Coordinator. Shards insert requests using **Consistent Hashing** (MD5) and queries workers in parallel using **Scatter-Gather**.
*   **`knowledge_graph.py`** [knowledge_graph.py](file:///D:/My%20Own%20Artificial%20Intelligance/knowledge_graph.py) (Feature 09): Extracts entities and relationships from documents using Ollama and stores them in Neo4j to run hybrid Vector + Graph RAG.
*   **`query_parser.py`** [query_parser.py](file:///D:/My%20Own%20Artificial%20Intelligance/query_parser.py) (Feature 10): Lexer & Parser (sly) that compiles a SQL-like DSL query (e.g. `SELECT * FROM vectors WHERE category = 'cs'`) into native API search execution calls.
*   **`reranker.py`** [reranker.py](file:///D:/My%20Own%20Artificial%20Intelligance/reranker.py): Uses a neural cross-encoder model to re-score and re-rank search results, achieving superior semantic accuracy.

---

## 2. Environment Setup

To run advanced modes, ensure external services are running (though the app falls back gracefully to dry-run modes if they are offline):

*   **Ollama**: Install from [ollama.com](https://ollama.com) and pull models:
    ```bash
    ollama pull nomic-embed-text
    ollama pull llama3
    ```
*   **Docker Services** (Optional for Kafka, Neo4j, Redis):
    ```bash
    # Run the cluster profile to spin up Kafka, Neo4j, Redis, and workers
    docker compose --profile cluster up -d
    ```

---

## 3. Step-by-Step Feature Testing & Demo Data

### ── FEATURE 01: Single-Node Search & 3D Visualization
Test the core database, HNSW searches, and visual spatial distribution.

1.  **Start Main Server**:
    ```bash
    python main.py
    ```
2.  **Access Web UI**: Open `http://localhost:8080` in your browser.
3.  **Insert Test Vectors**: Go to the **Visualize** tab and insert vectors manually:
    *   **Text/Meta**: `Heap Sort Algorithm` | **Category**: `cs` | **Vector**: `0.1, -0.2, 0.5, 0.1, 0.0, 0.8, -0.3, 0.2, 0.1, -0.1, 0.4, 0.2, -0.2, 0.1, 0.0, 0.5`
    *   **Text/Meta**: `Margarita Pizza recipe` | **Category**: `food` | **Vector**: `0.8, 0.5, -0.1, 0.0, 0.2, -0.3, 0.1, 0.0, -0.2, 0.4, 0.1, 0.8, 0.5, -0.1, 0.2, 0.1`
    *   **Text/Meta**: `Neural Networks backpropagation` | **Category**: `cs` | **Vector**: `0.2, -0.1, 0.6, 0.2, 0.0, 0.7, -0.2, 0.1, 0.2, -0.2, 0.5, 0.1, -0.1, 0.2, 0.1, 0.6`
4.  **Perform Search**: Go to the **Search** tab. Type a search query like `sorting algorithm` or `pizza` and choose **HNSW** or **Hybrid**. Check how the 3D plot highlights matches.

---

### ── FEATURE 02: GPU-Accelerated Search Index
Test PyTorch flat CUDA/CPU index execution.

1.  **UI Method**: In the **Search** tab, select the **GPU** pill under the "Algorithm" section and click search.
2.  **API Method (cURL)**:
    ```bash
    curl -X GET "http://localhost:8080/search?v=0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.0,0.1,0.2,0.3,0.4,0.5,0.6&k=3&algo=gpu"
    ```
3.  **Validate**: Verify that the API output returns `"algo": "gpu"` and executes in microseconds (`"us"`).

---

### ── FEATURE 03: Consensual Sharding & Raft Cluster
Test consistent hash routing and consensus write replication.

1.  **Start Workers** (Open 3 separate terminals):
    *   **Terminal 1**:
        ```bash
        python worker.py --port 8081 --node-id worker-1 --raft-host 127.0.0.1 --raft-port 8181 --partners 127.0.0.1:8182,127.0.0.1:8183
        ```
    *   **Terminal 2**:
        ```bash
        python worker.py --port 8082 --node-id worker-2 --raft-host 127.0.0.1 --raft-port 8182 --partners 127.0.0.1:8181,127.0.0.1:8183
        ```
    *   **Terminal 3**:
        ```bash
        python worker.py --port 8083 --node-id worker-3 --raft-host 127.0.0.1 --raft-port 8183 --partners 127.0.0.1:8181,127.0.0.1:8182
        ```
2.  **Start Coordinator**:
    ```bash
    python coordinator.py
    ```
3.  **UI Cluster Dashboard**: Open the **Cluster** tab on `http://localhost:8080`. You will see all 3 worker cards instantly light up green (**Online**) and display their current Raft consensus role (**Leader 👑** or **Follower**).
4.  **Test Replication**: Run an insert to the Coordinator (`http://localhost:8080` or `http://localhost:8089` depending on your environment):
    ```bash
    curl -X POST "http://localhost:8080/insert" -H "Content-Type: application/json" -d "{\"doc_id\": \"test-doc-99\", \"embedding\": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6], \"metadata\": {\"title\": \"Consensus Document\"}}"
    ```
5.  **Validate**: Look at the Cluster tab. You will see the **Log Size** and **Vectors** count increment across all worker nodes.

---

### ── FEATURE 04: Async Ingestion (Kafka)
Test non-blocking queuing for documents.

1.  **Simulate Async Upload**: Upload a PDF or Text document via the **Docs** tab.
2.  **Async Status Check**:
    If Kafka is running, the server will reply immediately with `202 Accepted` and a `task_id`. The UI will poll the status until it turns to `COMPLETED`.
    *   **Manual Endpoint Test**:
        ```bash
        curl -X GET "http://localhost:8080/doc/status/<task_id>"
        ```

---

### ── FEATURE 05: GraphRAG Querying (Neo4j + Ollama)
Test combining vector matching with Knowledge Graph traversal.

1.  **Insert Graph Knowledge**: Go to the **Docs** tab and paste the following paragraphs:
    > "Albert Einstein was a theoretical physicist who developed the theory of relativity. Einstein was born in Germany. He won the Nobel Prize in Physics in 1921."
2.  **Select GraphRAG**: Go to the **AI RAG** tab. Toggle **GraphRAG** to **ON**.
3.  **Ask Question**:
    *   *Question*: `Where was Einstein born and what theory did he develop?`
4.  **Validate**: In the chat response, review how it pulls extracted graph triples: `(Albert Einstein)-[developed]->(theory of relativity)` to formulate the final answer.

---

### ── FEATURE 06: SQL DSL Query Console
Test the lexer, parser, and search compiler.

Go to the **SQL Query** tab in the UI and execute the following SQL console queries:

#### Case 1: Simple Filter query
```sql
SELECT * FROM vectors WHERE category = 'cs'
```
*   *Expected behavior*: Filters and lists only elements matching category `cs`.

#### Case 2: Semantic Vector search with filter
```sql
SELECT * FROM vectors WHERE category = 'cs' AND vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6] LIMIT 3
```
*   *Expected behavior*: Performs a KNN similarity search matching the vector parameter, filtered by `cs`, returning the top 3 nearest items.

#### Case 3: Lexical Keyword + Semantic hybrid search
```sql
SELECT * FROM vectors WHERE match('sorting') AND vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
```
*   *Expected behavior*: Triggers **Hybrid Search** combining lexical scoring (`match('sorting')`) and vector similarity.

---

### ── FEATURE 07: Neural Re-ranking & IVF-PQ Compression
1.  **Neural Re-ranking**: In the **AI RAG** tab, toggle **Cross-Encoder Re-ranker** to **ON**. This will re-score retrieved document chunks to ensure only the highest contextually relevant text is fed to the LLM.
2.  **Memory Compression**: In the **Search** tab, locate the **IVF-PQ** panel. Click **Train Index**. It will compress the vectors using Product Quantization and output saved memory statistics.
