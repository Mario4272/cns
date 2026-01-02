# Phase 6: Vector Index v0 (Slice 2)

**Status**: Slice 2 Delivered
**Goal**: Correct, deterministic, pluggable vector search.

## 1. Contract
- **Interface**: `cns_py.vector.VectorIndex` (ABC)
- **Methods**:
    - `upsert(id, vector, metadata?)`
    - `delete(id)`
    - `query(vector, k=10) -> List[(id, score)]`
- **Metric**: Cosine Similarity.
    - Internally normalized (L2).
    - Query computes Dot Product of normalized vectors. 
    - Range: -1.0 to 1.0 (1.0 = identical).
- **Determinism**:
    - Tie-breaking: If scores are equal, sort by `ID ASC`.
    - `ExactInMemoryIndex`: Sort key `(-score, id)`.
    - `PgVectorIndex`: Sort clause `ORDER BY (embedding <=> query) ASC, id ASC`.

## 2. Backends
### ExactInMemoryIndex (Default)
- **Tech**: Numpy / Pure Python.
- **Usage**: Dev, CI, small datasets.
- **Persistence**: None (in-memory only).

### PgVectorIndex
- **Tech**: Postgres `pgvector` extension.
- **Schema**: Table `vector_store` (`id TEXT PK`, `embedding vector(384)`).
- **Usage**: Production, large datasets.
- **Config**: Activated via `CNS_VECTOR_BACKEND=pg`.

## 3. Integration
- **API**: `POST /graph/similar`
- **Payload**: `{"vector": [...], "k": 10}`
- **Response**: `{"results": [{"id": "...", "score": ...}]}`

## 4. Verification
- **Unit Tests**: `tests/test_vector_index.py` (Covers upsert logic, normalization, determinism).
- **Integration**: `tests/test_api_server.py` (Covers API wiring).
- **Perf**: P95 Latency budget < 250ms maintained.
