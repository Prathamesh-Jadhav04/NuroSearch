import sys
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ivfpq import IVFPQIndex
from tests.benchmark_gate import random_vector

def test_ivfpq_basic():
    # IVFPQ needs DIM to be divisible by M. Let's use DIM=16, M=4 (sub_dim = 4)
    # C=5 (5 centroids because we only have 20 training vectors)
    index = IVFPQIndex(dim=16, M=4, C=5, n_probe=2)
    
    # Generate some vectors
    vectors = [random_vector(16) for _ in range(20)]
    vectors_np = np.array(vectors, dtype=np.float32)
    
    index.train(vectors_np)
    assert index.is_trained
    
    # Add vectors
    for i, v in enumerate(vectors):
        index.add(i, v)
        
    # Search
    query = random_vector(16)
    results = index.search(query, k=5)
    assert len(results) <= 5
    
    # Memory size check
    mem = index.memory_bytes()
    assert mem == 20 * 4 # 20 vectors * 4 bytes each
