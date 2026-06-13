"""
NuroSearch Worker Node
Holds a shard of the vector index. Receives forwarded requests from coordinator.
Uses PySyncObj (Raft consensus) to replicate writes across worker nodes.

Run instances:
  python worker.py --port 8081 --node-id worker-1 --raft-port 8181 --partners localhost:8182,localhost:8183
  python worker.py --port 8082 --node-id worker-2 --raft-port 8182 --partners localhost:8181,localhost:8183
  python worker.py --port 8083 --node-id worker-3 --raft-port 8183 --partners localhost:8181,localhost:8182
"""

import argparse
import time
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from pysyncobj import SyncObj, replicated

# Import HNSW index
from hnsw import HNSWIndex, cosine_distance

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8081)
parser.add_argument('--node-id', type=str, default='worker-1')
parser.add_argument('--raft-host', type=str, default='localhost')
parser.add_argument('--raft-port', type=int, default=8181)
parser.add_argument('--partners', type=str, default='')
parser.add_argument('--dim', type=int, default=16)
args = parser.parse_args()

app = Flask(__name__)
CORS(app)

# Initialize local HNSW index
local_index = HNSWIndex(dim=args.dim)

class ReplicatedVectorLog(SyncObj):
    """
    Raft-replicated write log for NuroSearch.
    Ensures all active nodes agree on every insert before confirming.
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
        # Apply to local HNSW graph
        local_index.insert(doc_id, embedding)
        print(f"[{args.node_id}] Raft committed insert: {doc_id}")

# Parse partners
partner_list = [p.strip() for p in args.partners.split(',') if p.strip()]

# Initialize SyncObj Raft replication
raft_addr = f'{args.raft_host}:{args.raft_port}'
print(f"[{args.node_id}] Initializing Raft on {raft_addr} with partners {partner_list}...")
raft = ReplicatedVectorLog(raft_addr, partner_list)

@app.route('/insert', methods=['POST'])
def worker_insert():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    doc_id = data.get('doc_id') or data.get('id')
    embedding = data.get('embedding') or data.get('emb')
    metadata = data.get('metadata', {})
    
    if doc_id is None or not embedding:
        return jsonify({"error": "Missing id or embedding"}), 400
        
    try:
        # Replicate write using Raft consensus
        # Wait until replication finishes or timeout
        t0 = time.time()
        raft.append_insert(doc_id, embedding, metadata)
        
        # PySyncObj is asynchronous by default, but we want consensus confirmation
        # We can wait a brief moment to confirm replication to majority
        while time.time() - t0 < 2.0:
            # Check if this node has registered it
            if doc_id in [op['doc_id'] for op in raft._log]:
                break
            time.sleep(0.05)
            
        return jsonify({
            "status": "inserted",
            "node": args.node_id,
            "raft_status": "synced" if doc_id in [op['doc_id'] for op in raft._log] else "pending"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['GET'])
def worker_search():
    v_str = request.args.get('v', '')
    if not v_str:
        return jsonify({"results": [], "node": args.node_id})
    try:
        v = [float(x) for x in v_str.split(',') if x]
    except ValueError:
        return jsonify({"error": "Invalid vector"}), 400
        
    k = int(request.args.get('k', 5))
    
    # Query HNSW locally
    raw_ids = local_index.search(v, k)
    
    # Format results with distances
    results = []
    # Since HNSWIndex search only returns ids, let's find the vectors to compute distances
    # We can search through the raft log or local index graph
    for item_id in raw_ids:
        # Find item in log to get embedding for distance
        vector = None
        for op in raft._log:
            if op['doc_id'] == item_id:
                vector = op['embedding']
                break
        if vector:
            dist = cosine_distance(v, vector)
            results.append({
                "id": item_id,
                "score": float(1.0 - dist), # Cosine similarity
                "distance": float(dist),    # Cosine distance
                "node": args.node_id
            })
            
    return jsonify({"results": results, "node": args.node_id})

@app.route('/health')
def health():
    # Return PySyncObj cluster state info
    leader = raft._getLeader()
    return jsonify({
        "status": "ok",
        "node": args.node_id,
        "raft_leader": str(leader) if leader else None,
        "raft_is_leader": raft._isLeader(),
        "log_size": len(raft._log),
        "vectors": len(local_index.hnsw.G)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=args.port)
