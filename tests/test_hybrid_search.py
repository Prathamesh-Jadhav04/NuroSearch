import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import VectorDB, SQLiteDB, get_dist_fn

def test_hybrid_search():
    # In-memory DB
    sqldb = SQLiteDB(":memory:")
    vdb = VectorDB(16, sqldb)
    
    # Insert a couple of vectors
    v1 = [0.1] * 16
    v2 = [0.9] * 16
    
    vdb.insert("apple pie", "fruit", v1, get_dist_fn("cosine"))
    vdb.insert("banana split", "fruit", v2, get_dist_fn("cosine"))
    
    res = vdb.hybrid_search(v1, "apple", k=2, metric="cosine")
    assert "hits" in res
    assert len(res["hits"]) > 0
    assert res["hits"][0]["meta"] == "apple pie"
