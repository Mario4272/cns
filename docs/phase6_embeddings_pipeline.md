# Phase 6: Embeddings Pipeline

**Status**: Delivered (Slice 5B)
**Goal**: Decouple vector generation from index management.

## 1. Architecture
The `IndexManager` delegates vectorization to an `EmbeddingProvider`.
- **Atom** -(text)-> **IndexManager** -(list[str])-> **Provider** -(list[vec])-> **Index**.

## 2. Interfaces
### `EmbeddingProvider` (ABC)
File: `cns_py/vector/embeddings.py`
Methods:
- `embed_texts(texts: List[str]) -> List[List[float]]`: Batch embedding.
- `dimension -> int`: Returns output vector dimension.

### `DeterministicStubProvider` (Default)
Used for testing and deterministic validation.
- **Logic**: MD5(text) -> Seed -> Random Vector (Normalized).
- **Determinism**: 100%. Same text always yields same vector.

## 3. Usage
To integrate a real model (e.g. OpenAI, HuggingFace):
1. Implement `EmbeddingProvider`.
2. Update `IndexManager.__init__` (or inject via config) to use the new provider.

## 4. Re-indexing
Trigger a full re-index to regenerate vectors for all `Entity`/`Concept` atoms:
```python
manager.rebuild()
```
This will:
1. Fetch all eligible atoms from DB.
2. Extract text (fallback to label).
3. Batch embed using current provider.
4. Bulk load into the backend.
