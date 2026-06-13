import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hnsw import HNSWIndex
from tests.benchmark_gate import random_vector, brute_force_topk

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
