# RFC: Phase 6 Vector Index (Rust)

## 1. Overview
This document defines the architecture for the **Rust Vector Index** component of CNS.
Goal: Replace `pgvector` hybrid search with a high-performance, in-memory Rust engine capable of <10ms ANN queries.

## 2. Algorithm & Metric
### Algorithm: HNSW (Hierarchical Navigable Small World)
- **Why**: Industry standard for recall/latency trade-off (used in Weaviate, Qdrant, Chroma).
- **Implementation**:
    - **Alpha 1**: `FlatIndex` (Exact Search) - Implemented in Phase 6. used for correctness verification.
    - **Alpha 2**: `HNSW` (ANN) - To be implemented using `hora` or `faiss` bindings.
- **Decision**: Start with `FlatIndex`, migrate to `HNSW` when N > 10k.

### Metric: Cosine Similarity
- **Why**: Standard for semantic search embeddings (OpenAI, etc.).
- **Formula**: `(A · B) / (||A|| * ||B||)`
- **Optimization**: Normalized vectors allow using Dot Product for speed.

## 3. API Sketch
The `VectorIndex` trait in `cns_rust` will expose:

```rust
struct VectorEmbedding([f32; 1536]); // e.g. OpenAI size

trait VectorIndex {
    /// Batch insert/update embeddings
    async fn upsert(&self, items: Vec<(u64, VectorEmbedding)>) -> Result<()>;

    /// Approximate Nearest Neighbor search
    async fn search(&self, query: VectorEmbedding, k: usize) -> Result<Vec<u64>>;

    /// Remove item by ID
    async fn delete(&self, id: u64) -> Result<()>;
    
    /// Bulk load from Arrow/Parquet (Fast Path)
    async fn bulk_load(&self, path: &Path) -> Result<()>;
}
```

## 4. Persistence Stance (Alpha)
- **Scope**: **In-Memory Only** for Phase 6 Alpha.
- **Rationale**: Focus on query latency and correctness first.
- **Cold Start**: Rehydrate from Postgres/Parquet on startup.
- **Future**: Memory mapping (mmap) or distinct serialization.

## 5. Filtering Stance
- **Scope**: **Post-Filtering**.
- **Mechanism**:
    1.  Fetch `k * m` candidates from ANN index (over-fetching).
    2.  Filter against Metadata Store (e.g., `observed_at`, `predicate`).
    3.  Return top `k`.
- **Reasoning**: Pre-filtering (filtered HNSW) is complex. Post-filtering is sufficient for MVP scale (<1M vectors).
