
"""
Vector Benchmark Script.
Compares configured backend vs ExactInMemoryIndex (Oracle).
Metrics: Build Time, Latency P50/P95, Recall@K.
"""
import time
import numpy as np
import argparse
import os
import logging
from typing import List, Tuple

# Ensure we can import cns_py
import sys
sys.path.append(os.getcwd())

from cns_py.vector import ExactInMemoryIndex, PgVectorIndex, VectorIndex
try:
    from cns_py.vector.hnsw_index import HnswVectorIndex
    HNSW_AVAIL = True
except ImportError:
    HNSW_AVAIL = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bench")

def generate_data(count: int, dim: int) -> List[Tuple[str, List[float]]]:
    """Generate random normalized vectors."""
    logger.info(f"Generating {count} vectors (dim={dim})...")
    rng = np.random.RandomState(42)
    vecs = rng.randn(count, dim).astype('float32')
    # Normalize
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs = vecs / norms
    
    data = []
    for i in range(count):
        data.append((f"doc_{i}", vecs[i].tolist()))
    return data

def bench_index(name: str, index: VectorIndex, data: List, queries: List, k: int = 10):
    logger.info(f"--- Benchmarking {name} ---")
    
    # 1. Build
    start_t = time.time()
    # Prepare bulk load format
    items = [(d[0], d[1], {}) for d in data]
    index.bulk_load(items)
    build_time = time.time() - start_t
    logger.info(f"Build Time: {build_time:.4f}s")
    
    # 2. Query
    latencies = []
    results_map = {} # query_idx -> set of doc_ids
    
    start_q = time.time()
    for i, q_vec in enumerate(queries):
        t0 = time.time()
        res = index.query(q_vec, k=k)
        latencies.append(time.time() - t0)
        results_map[i] = {r[0] for r in res}
        
    total_q = time.time() - start_q
    
    latencies = np.array(latencies) * 1000 # ms
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    qps = len(queries) / total_q
    
    logger.info(f"Latency P50: {p50:.2f}ms")
    logger.info(f"Latency P95: {p95:.2f}ms")
    logger.info(f"QPS: {qps:.1f}")
    
    return results_map

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--dim", type=int, default=384)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    
    # Data
    full_data = generate_data(args.count + args.queries, args.dim)
    dataset = full_data[:args.count]
    queries_data = full_data[args.count:]
    queries = [x[1] for x in queries_data]
    
    # Oracle (Exact)
    oracle_idx = ExactInMemoryIndex()
    oracle_res = bench_index("ExactInMemory (Oracle)", oracle_idx, dataset, queries, args.k)
    
    # Candidates
    candidates = []
    if HNSW_AVAIL:
        candidates.append(("HNSW", HnswVectorIndex(dim=args.dim, max_elements=args.count)))
    else:
        logger.warning("HNSW not avail.")
        
    # TODO: Add Pg integration bench if env var set? 
    # For now focused on HNSW vs Memory
    
    for name, idx in candidates:
        cand_res = bench_index(name, idx, dataset, queries, args.k)
        
        # Calculate Recall
        recalls = []
        for i in range(len(queries)):
            truth = oracle_res[i]
            pred = cand_res[i]
            # Recall = Intersection / K
            # (Assuming truth always returns K, or at least max possible)
            if not truth:
                continue
            match = len(truth.intersection(pred))
            recalls.append(match / len(truth))
            
        avg_recall = np.mean(recalls)
        logger.info(f"{name} Recall@{args.k}: {avg_recall:.4f}")
        
        if avg_recall < 0.9:
            logger.warning(f"{name} Recall is below 0.9!")

if __name__ == "__main__":
    main()
