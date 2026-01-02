# Phase 6: Vector Search Filtering (Slice 3C)

**Status**: Shipped
**Goal**: Enable gated vector search using metadata constraints.

## Contract
The `query` method supports an optional `filter` argument:
```python
query(vector: Vector, k: int=10, filter: Optional[Dict[str, Any]] = None)
```

## Logic
- **Constraint Model**: Subset Match.
    - If `filter` is provided, a candidate document matches ONLY IF its metadata contains all key-value pairs specified in the filter.
    - `filter={"a": 1}` matches `metadata={"a": 1, "b": 2}`.
    - `filter={"a": 1}` DOES NOT match `metadata={"a": 2}`.
    - `filter={"a": 1}` DOES NOT match `metadata={}`.
- **Backends**:
    - `ExactInMemoryIndex`: Iterates and applies dictionary subset check.
    - `PgVectorIndex`: Uses JSONB containment operator `@>`.

## usage
```python
# Find similar vectors that are also of kind 'Entity'
results = index.query(query_vec, k=5, filter={"kind": "Entity"})
```

## Verification
- **Test**: `tests/test_vector_filtering.py` verifies inclusion, exclusion, and conjunction (AND) logic.
- **Determinism**: Filtered results maintain stable sort order (Score Desc, ID Asc).
