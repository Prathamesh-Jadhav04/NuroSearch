"""
NuroSearch Coordinator Node
Routes INSERT and SEARCH requests across worker nodes using consistent hashing.
Implements scatter-gather for search queries.
"""

import hashlib
import requests as req
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from flask_cors import CORS

import os

app = Flask(__name__)
CORS(app)

# Worker node registry — configurable for Docker via env vars
_default_workers = "worker-1=http://127.0.0.1:8081,worker-2=http://127.0.0.1:8082,worker-3=http://127.0.0.1:8083"
_worker_env = os.environ.get("WORKER_URLS", _default_workers)
WORKERS = []
for entry in _worker_env.split(","):
    entry = entry.strip()
    if "=" in entry:
        wid, wurl = entry.split("=", 1)
        WORKERS.append({"id": wid.strip(), "url": wurl.strip(), "alive": True})
    else:
        WORKERS.append({"id": f"worker-{len(WORKERS)+1}", "url": entry.strip(), "alive": True})

def get_worker_for_id(doc_id: str) -> dict:
    """
    Consistent hashing: map doc_id to a specific worker node.
    Same doc_id always routes to the same worker (stable sharding).
    """
    hash_value = int(hashlib.md5(str(doc_id).encode()).hexdigest(), 16)
    alive_workers = [w for w in WORKERS if w["alive"]]
    if not alive_workers:
        # Fall back to all if none marked alive (auto-retry check)
        alive_workers = WORKERS
    return alive_workers[hash_value % len(alive_workers)]

@app.route('/insert', methods=['POST'])
def coordinator_insert():
    """Route insert to the correct worker based on doc_id hashing."""
    data = request.json
    doc_id = data.get('doc_id') or data.get('id')
    if doc_id is None:
        return jsonify({"error": "Missing doc_id or id"}), 400
    
    worker = get_worker_for_id(str(doc_id))
    try:
        response = req.post(f"{worker['url']}/insert", json=data, timeout=5)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to forward insert to worker {worker['id']}: {str(e)}"}), 500

@app.route('/search', methods=['GET'])
def coordinator_search():
    """Scatter search to all workers, gather results, merge top-K."""
    params = request.args
    k = int(params.get('k', 5))
    
    all_results = []
    
    def query_worker(worker):
        try:
            response = req.get(f"{worker['url']}/search", params=params, timeout=5)
            if response.status_code == 200:
                worker['alive'] = True
                return response.json().get('results', [])
            return []
        except Exception:
            worker['alive'] = False
            return []
    
    # Try querying only alive workers first, or all if none is active
    alive_workers = [w for w in WORKERS if w["alive"]]
    if not alive_workers:
        alive_workers = WORKERS
        
    with ThreadPoolExecutor(max_workers=len(alive_workers)) as executor:
        futures = {executor.submit(query_worker, w): w for w in alive_workers}
        for future in as_completed(futures):
            all_results.extend(future.result())
            
    # Gather: merge and return global top-K (sorted by distance ascending, i.e. closest first)
    # Each result is expected to have 'distance' or 'score'
    all_results.sort(key=lambda x: x.get('distance', x.get('score', float('inf'))))
    merged = all_results[:k]
    
    active_queried = len([w for w in alive_workers if w["alive"]])
    return jsonify({"results": merged, "nodes_queried": active_queried})

@app.route('/health')
def coordinator_health():
    # Gather health from workers
    worker_healths = []
    for w in WORKERS:
        try:
            res = req.get(f"{w['url']}/health", timeout=2)
            if res.status_code == 200:
                w['alive'] = True
                worker_healths.append(res.json())
            else:
                w['alive'] = False
                worker_healths.append({"id": w['id'], "status": "down"})
        except Exception:
            w['alive'] = False
            worker_healths.append({"id": w['id'], "status": "down"})
            
    return jsonify({
        "status": "ok",
        "workers": worker_healths
    })

if __name__ == '__main__':
    app.run(port=8090)
