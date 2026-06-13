"""
NuroSearch Benchmark Gate
Runs on every CI push. Fails if Recall@10 < RECALL_THRESHOLD.
Also generates benchmark_report.json for artifact storage.
"""

import time
import json
import sys
import random
import threading
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hnsw import HNSWIndex          # Import your HNSW class
from kd_tree import KDTreeIndex     # Import your KD-Tree class

RECALL_THRESHOLD = 0.85
DIM = 16                            # Use 16D demo vectors for CI (fast)
N_VECTORS = 1000
N_QUERIES = 100
K = 10

def random_vector(dim):
    v = [random.gauss(0, 1) for _ in range(dim)]
    mag = sum(x**2 for x in v) ** 0.5
    return [x / mag for x in v]

def cosine_distance(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return 1.0 - dot

def brute_force_topk(vectors, query, k):
    scored = [(i, cosine_distance(query, v)) for i, v in enumerate(vectors)]
    scored.sort(key=lambda x: x[1])
    return [i for i, _ in scored[:k]]

def compute_recall(approx_results, exact_results, k):
    """Recall@K = |approx ∩ exact| / K"""
    return len(set(approx_results[:k]) & set(exact_results[:k])) / k

def measure_qps(search_fn, queries, k, duration_sec=5):
    """Run search_fn for duration_sec seconds, count queries completed."""
    count = 0
    start = time.time()
    idx = 0
    while time.time() - start < duration_sec:
        search_fn(queries[idx % len(queries)], k)
        count += 1
        idx += 1
    return count / duration_sec

def run_benchmarks():
    print("=" * 60)
    print("NuroSearch Benchmark Gate")
    print("=" * 60)

    # Generate dataset
    print(f"\nGenerating {N_VECTORS} random {DIM}D vectors...")
    vectors = [random_vector(DIM) for _ in range(N_VECTORS)]
    queries = [random_vector(DIM) for _ in range(N_QUERIES)]

    # Build HNSW index
    print("Building HNSW index...")
    hnsw = HNSWIndex(dim=DIM, M=16, ef_build=200)
    t0 = time.time()
    for i, v in enumerate(vectors):
        hnsw.insert(i, v)
    hnsw_build_time = time.time() - t0
    print(f"  HNSW build time: {hnsw_build_time:.3f}s")

    # Compute Recall@K
    print(f"\nComputing Recall@{K} over {N_QUERIES} queries...")
    recalls = []
    hnsw_latencies = []
    for q in queries:
        exact = brute_force_topk(vectors, q, K)
        t0 = time.perf_counter()
        approx = hnsw.search(q, K)
        hnsw_latencies.append((time.perf_counter() - t0) * 1e6)  # microseconds
        recalls.append(compute_recall(approx, exact, K))
    
    mean_recall = sum(recalls) / len(recalls)
    mean_latency_us = sum(hnsw_latencies) / len(hnsw_latencies)
    p99_latency_us = sorted(hnsw_latencies)[int(0.99 * len(hnsw_latencies))]

    print(f"  Recall@{K}:        {mean_recall:.4f}")
    print(f"  Mean latency:    {mean_latency_us:.1f} µs")
    print(f"  P99 latency:     {p99_latency_us:.1f} µs")

    # Measure QPS
    print(f"\nMeasuring QPS (5s window)...")
    qps = measure_qps(lambda q, k: hnsw.search(q, k), queries, K)
    print(f"  HNSW QPS:        {qps:.1f}")

    # Build report
    report = {
        "recall_at_k": round(mean_recall, 4),
        "k": K,
        "n_vectors": N_VECTORS,
        "n_queries": N_QUERIES,
        "hnsw_build_time_sec": round(hnsw_build_time, 3),
        "mean_latency_microsec": round(mean_latency_us, 1),
        "p99_latency_microsec": round(p99_latency_us, 1),
        "qps": round(qps, 1),
        "threshold": RECALL_THRESHOLD,
        "passed": mean_recall >= RECALL_THRESHOLD
    }

    # Save report
    with open("benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to benchmark_report.json")

    # CI Gate
    print("\n" + "=" * 60)
    if mean_recall < RECALL_THRESHOLD:
        print(f"FAIL: Recall@{K} = {mean_recall:.4f} < threshold {RECALL_THRESHOLD}")
        print("This means HNSW graph quality has degraded. Check M, ef_build parameters.")
        sys.exit(1)
    else:
        print(f"PASS: Recall@{K} = {mean_recall:.4f} >= threshold {RECALL_THRESHOLD}")
        sys.exit(0)

if __name__ == "__main__":
    run_benchmarks()
