# Phase 6: ANN Backend (Experimental)

**Status**: Experimental (Slice 5A)
**Goal**: High-performance approximate search for large datasets.

## 1. Overview
The `HnswVectorIndex` backend provides Approximate Nearest Neighbor (ANN) search using the `hnswlib` library. It offers faster query times and efficient build scaling at the cost of slightly reduced recall (typically >0.95 for structured data, >0.8 for random noise).

## 2. Configuration
- **Enable**: Set `VECTOR_INDEX_BACKEND=ann`
- **Path**: Set `VECTOR_INDEX_PATH` (e.g., `.cns_vector_index/ann_index`)

## 3. Implementation Details
- **Library**: `hnswlib` (Python bindings).
- **Metric**: Inner Product (`ip`) on normalized vectors (equivalent to Cosine Similarity).
- **Parameters**:
  - `M=48`: Number of bi-directional links per element.
  - `ef_construction=800`: Size of the dynamic list for the nearest neighbors (used during index construction). High value = better quality, slower build.
  - `ef` (Search): Dynamic based on `k` (approx `k * 5` to `k * 10`), guaranteeing high recall.

## 4. Known Limitations
- **Determinism**: HNSW is theoretically deterministic if single-threaded and seeded, but floating point operations order might vary slightly. We force `count` seeding on bulk load but upsert order matters.
- **Recall**: On uniform random noise datasets (Sphere), recall might drop below 0.9. Real-world embedding manifolds yield much better performance.
- **Persistence**: Saves two files: `.hnsw` (binary index) and `.meta.pkl` (ID mappings).

## 5. Benchmarking
Run `python scripts/vector_bench.py` to compare `ExactInMemoryIndex` vs `HnswVectorIndex`.
