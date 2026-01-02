# Phase 6: Vector Index Persistence (Slice 3A)

**Status**: Shipped
**Goal**: Enable saving/loading of the vector index to/from disk.

## Interface
The `VectorIndex` contract now includes:
- `save(path: str)`: Persist state to the given path prefix.
- `load(path: str)`: Restore state from the given path prefix.

## Implementations

### ExactInMemoryIndex
- **Format**: Two files per configured path:
    1. `{path}.npz` (Compressed Numpy Archive): Stores vectors and IDs.
        - Arrays: `ids` (string keys), `vectors` (float32 matrix).
    2. `{path}.meta.json` (JSON Metadata): Stores configuration and auxiliary data.
        - Fields: `version` (e.g., "v1"), `dim`, `count`, `metadata` (dict).
- **Versioning**: Enforced via `version` field in JSON. Loading checks compatibility or raises `ValueError`.
- **Determinism**: Save logic sorts IDs before writing to ensure binary stability of the `.npz` file across identical states.

### PgVectorIndex
- **Mechanism**: Use standard PostgreSQL tools (`pg_dump`, WAL, Point-in-Time Recovery).
- **Methods**: `save` and `load` raise `NotImplementedError` to indicate that management is external to the application layer.

## Verification
- **Roundtrip**: `tests/test_vector_persistence.py` confirms that loading a saved index restores exact vectors and metadata.
- **Determinism**: Tie-breaking behavior is preserved after reload.
