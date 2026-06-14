import sys
import json
import requests

PORT = 7860
BASE_URL = f"http://localhost:{PORT}"

def check_server():
    for port in [7860, 8080]:
        url = f"http://localhost:{port}"
        try:
            r = requests.get(f"{url}/status", timeout=2)
            if r.status_code == 200:
                return url
        except Exception:
            pass
    return None

def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title.upper():^58}")
    print("=" * 60)

def run_get_test(endpoint, description):
    print(f"\n[TEST] {description}")
    print(f"  GET {BASE_URL}{endpoint}")
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"  Status Code: {r.status_code}")
        print("  Response Preview:")
        data = r.json()
        if isinstance(data, list):
            print(json.dumps(data[:3], indent=2))
            if len(data) > 3:
                print(f"  ... ({len(data)} items total)")
        else:
            # truncate large dicts
            preview = {k: v for k, v in list(data.items())[:8]}
            print(json.dumps(preview, indent=2))
            if len(data) > 8:
                print("  ... (truncated)")
    except Exception as e:
        print(f"  [ERROR] {e}")

def run_post_test(endpoint, payload, description, timeout=10):
    print(f"\n[TEST] {description}")
    print(f"  POST {BASE_URL}{endpoint}")
    print(f"  Payload: {json.dumps(payload)}")
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=timeout)
        print(f"  Status Code: {r.status_code}")
        print("  Response:")
        print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"  [ERROR] {e}")

def run_stream_post_test(endpoint, payload, description):
    print(f"\n[TEST] {description}")
    print(f"  POST {BASE_URL}{endpoint} (Streaming)")
    print(f"  Payload: {json.dumps(payload)}")
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, stream=True, timeout=30)
        print(f"  Status Code: {r.status_code}")
        print("  Stream Response Processing:")
        tokens = []
        contexts = []
        for line in r.iter_lines():
            if line:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])
                        if data.get("type") == "context":
                            contexts = data.get("data", [])
                            print(f"    -> Context Retrieved: {len(contexts)} chunks")
                            for idx, c in enumerate(contexts[:2]):
                                print(f"       [{idx+1}] Title: \"{c.get('title')}\" (dist: {c.get('distance'):.4f})")
                            if len(contexts) > 2:
                                print(f"       ... and {len(contexts)-2} more chunks")
                        elif data.get("type") == "token":
                            tokens.append(data.get("data", ""))
                        elif data.get("type") == "error":
                            print(f"    -> [LLM Error]: {data.get('data')}")
                    except Exception as e:
                        pass
        if tokens:
            answer = "".join(tokens).replace("\n", " ").strip()
            print(f"    -> Generated Answer: {answer[:180]}...")
        else:
            print("    -> No answer tokens received (check if Ollama is running and has the model loaded)")
    except Exception as e:
        print(f"  [ERROR] {e}")

def run_tests():
    global BASE_URL
    detected_url = check_server()
    if not detected_url:
        print("[ERROR] Could not connect to NuroSearch server on port 7860 or 8080.")
        print("Please start the server first using: python main.py")
        sys.exit(1)
        
    BASE_URL = detected_url
    print(f"Connected to NuroSearch at: {BASE_URL}")

    # 1. Server Health & Stats
    print_header("1. Server Health & Stats")
    run_get_test("/status", "Check system status")
    run_get_test("/stats", "Get DB vector stats")
    run_get_test("/hnsw-info", "Get HNSW graph visualization info")

    # 2. Vector Operations (CRUD)
    print_header("2. Vector Insert & Delete")
    temp_vector = [0.1] * 16
    temp_vector[0] = 0.95 # normalize-ish
    insert_payload = {
        "metadata": "Temporary CLI test vector: AI and quantum systems",
        "category": "tech",
        "embedding": temp_vector
    }
    print("\n[TEST] Insert a temporary vector")
    inserted_id = None
    try:
        r = requests.post(f"{BASE_URL}/insert", json=insert_payload, timeout=5)
        print(f"  Status Code: {r.status_code}")
        res_data = r.json()
        print(f"  Response: {res_data}")
        inserted_id = res_data.get("id")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 3. Vector KNN Searches (Varying Algorithms)
    print_header("3. Vector Similarity Search Algorithms")
    
    # query representation for sports/games category
    query_vector = "0.9,0.1,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.3"
    
    run_get_test(f"/search?v={query_vector}&k=2&algo=hnsw&metric=cosine", "HNSW Index (Cosine Distance)")
    run_get_test(f"/search?v={query_vector}&k=2&algo=kdtree&metric=euclidean", "KD-Tree (Euclidean Distance)")
    run_get_test(f"/search?v={query_vector}&k=2&algo=bruteforce&metric=manhattan", "Brute-Force Search (Manhattan)")
    run_get_test(f"/search?v={query_vector}&k=2&algo=ivfpq&metric=cosine", "IVFPQ Vector Index")
    run_get_test(f"/search?v={query_vector}&k=2&algo=gpu&metric=cosine", "GPU Accelerated Search")

    # 4. NuroSearch Query Language Parser
    print_header("4. SQL-like Query Parser (/query)")
    
    # query parser doesn't support GTE operator, so we use EQ and GT/LT
    sql_payload_1 = {
        "query": "SELECT * FROM vectors WHERE category = 'sports' AND similarity > 0.70 LIMIT 2",
        "v": query_vector
    }
    run_post_test("/query", sql_payload_1, "Execute select sports query with similarity constraint")

    sql_payload_2 = {
        "query": "SELECT * FROM vectors WHERE category = 'tech' LIMIT 3"
    }
    run_post_test("/query", sql_payload_2, "Execute select tech query (using random vector fallback)")

    # 5. Benchmarking Features
    print_header("5. Performance Benchmarking")
    run_get_test(f"/benchmark?v={query_vector}&k=3&metric=cosine", "Get search algorithm latencies comparison")
    run_post_test("/benchmark/run", {}, "Trigger full benchmark suite test execution", timeout=60)

    # 6. Document & RAG Features
    print_header("6. Document Semantic Search & RAG")
    run_get_test("/doc/list", "List indexed documents")
    
    doc_search_payload = {
        "question": "space missions to mars Perseverance rover"
    }
    run_post_test("/doc/search", doc_search_payload, "Hybrid Document Search (BM25 + Semantic)")

    rag_payload = {
        "question": "What planets are in our solar system?"
    }
    run_stream_post_test("/doc/ask", rag_payload, "RAG Question Answering (Ollama)")

    graph_rag_payload = {
        "question": "Explain Mars exploration and discoveries"
    }
    run_stream_post_test("/doc/ask/graph", graph_rag_payload, "GraphRAG Multi-Hop Relational QA (Neo4j)")

    # 7. Cleanup
    print_header("7. Database Cleanup")
    if inserted_id:
        print(f"\n[TEST] Delete temporary vector ID {inserted_id}")
        try:
            r = requests.delete(f"{BASE_URL}/delete/{inserted_id}", timeout=5)
            print(f"  Status Code: {r.status_code}")
            print(f"  Response: {r.json()}")
        except Exception as e:
            print(f"  [ERROR] {e}")
    else:
        print("\n[SKIP] No temporary vector ID found to delete.")

if __name__ == "__main__":
    run_tests()
