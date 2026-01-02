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

## 2. Configuration & Lifecycle (Slice 4)
### Environment Variables
- `VECTOR_INDEX_ENABLED` (0/1): Master switch.
- `VECTOR_INDEX_BACKEND`: `memory` (default) or `pg`.
- `VECTOR_INDEX_PATH`: Filesystem path for `memory` backend persistence (e.g. `.cns_vector_index/index`).

### IndexManager
The `IndexManager` singleton handles:
- **Startup**: Loads persisted index (if `memory` backend and files exist) OR rebuilds index from DB atoms (`Entity` and `Concept` kinds).
- **Shutdown**: Persists index to disk (if `memory` backend).
- **Query**: Proxies to the underlying backend and **enriches** results with atom Label/Kind from DB.

## 3. Backends
### ExactInMemoryIndex (Default)
- **Tech**: Numpy / Pure Python.
- **Persistence**: `np.savez` + `json` metadata (See [Persistence Doc](phase6_vector_index_persistence.md)).

### PgVectorIndex
- **Tech**: Postgres `pgvector` extension.
- **Usage**: Production. Requires `vector` extension.

## 4. Integration
- **API**: `POST /graph/similar`
- **Enrichment**: Response includes `label` and `kind` fields fetched from DB.
- **Filtering**: Supports metadata subset matching (See [Filtering Doc](phase6_vector_filtering.md)).

## 5. Verification
- **Unit**: `tests/test_vector_index.py`.
- **Integration**: 
    - `tests/test_api_server.py`: API wiring & enrichment.
    - `tests/test_vector_lifecycle.py`: Startup/Shutdown persistence & DB rebuild.
- **Perf**: P95 < 250ms.

