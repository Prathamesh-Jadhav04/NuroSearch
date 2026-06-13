import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gpu_search import GPUSearchIndex

def test_gpu_search_basic():
    index = GPUSearchIndex(dim=4)
    # Vectors (already normalized roughly)
    vectors = [
        (1, [1.0, 0.0, 0.0, 0.0]),
        (2, [0.0, 1.0, 0.0, 0.0]),
        (3, [0.0, 0.0, 1.0, 0.0]),
    ]
    index.build(vectors)
    
    # Search for [1, 0, 0, 0]
    res = index.search([1.0, 0.0, 0.0, 0.0], k=1)
    assert len(res) == 1
    assert res[0][0] == 1  # doc_id
    assert abs(res[0][1] - 1.0) < 1e-5
    
    # Add a vector
    index.add(4, [0.0, 0.0, 0.0, 1.0])
    res = index.search([0.0, 0.0, 0.0, 1.0], k=1)
    assert len(res) == 1
    assert res[0][0] == 4
    
    # Batch search
    batch_res = index.batch_search([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], k=2)
    assert len(batch_res) == 2
    assert batch_res[0][0][0] == 1
    assert batch_res[1][0][0] == 2
    
    # Remove vector
    index.remove(4)
    res = index.search([0.0, 0.0, 0.0, 1.0], k=1)
    assert len(res) == 1
    assert res[0][0] != 4  # Should not be 4 since it was removed
    
    # Memory
    mem = index.memory_bytes()
    assert mem > 0
