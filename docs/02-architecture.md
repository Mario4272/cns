# CNS Architecture

## Overview

CNS is a **cognition-native substrate** that stores intelligence (atoms, fibers, aspects) with built-in support for belief, provenance, temporal reasoning, and in-store learning.

---

## Core Components

### 1. Storage Layer

#### Atoms Table
The fundamental unit of intelligence.

```sql
CREATE TABLE atoms (
  id BIGSERIAL PRIMARY KEY,
  kind TEXT NOT NULL,            -- Entity | Event | Rule | Program
  label TEXT NOT NULL,           -- human label or canonical name
  text TEXT,                     -- optional long text
  symbol JSONB,                  -- optional symbolic form (AST/Datalog/SMT)
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Kinds:**
- **Entity**: People, organizations, systems (e.g., "FrameworkX", "TLS1.3")
- **Event**: Temporal occurrences (e.g., "CVE-2024-1234 disclosed")
- **Rule**: Logic, constraints, policies (e.g., "TLS < 1.2 is non-compliant")
- **Program**: Executable code, learners (e.g., entity resolver, summarizer)

#### Fibers Table
Directed typed edges between atoms.

```sql
CREATE TABLE fibers (
  id BIGSERIAL PRIMARY KEY,
  src BIGINT NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
  dst BIGINT NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
  predicate TEXT NOT NULL,       -- relation type (e.g., "supports_tls", "requires")
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_fibers_src ON fibers(src);
CREATE INDEX idx_fibers_dst ON fibers(dst);
```

**Predicates** are application-defined:
- `supports_tls`, `requires`, `located_in`, `knows`, `same_as`, `contradicts`, etc.

#### Aspects Table
Co-resident properties for atoms and fibers.

```sql
CREATE TABLE aspects (
  id BIGSERIAL PRIMARY KEY,
  subject_kind TEXT NOT NULL CHECK (subject_kind IN ('atom','fiber')),
  subject_id BIGINT NOT NULL,
  
  -- Bitemporal tape
  valid_from TIMESTAMPTZ,        -- when it became true in the world
  valid_to   TIMESTAMPTZ,        -- when it stopped being true
  observed_at TIMESTAMPTZ DEFAULT now(),  -- when we learned about it
  
  -- Belief
  belief REAL,                   -- 0..1 confidence
  
  -- Provenance
  provenance JSONB,              -- {source_id, uri, hash, fetched_at, signature}
  
  -- Vectors (multi-space)
  embedding vector(384),         -- pgvector extension
  
  UNIQUE(subject_kind, subject_id)
);

CREATE INDEX idx_aspects_subject ON aspects(subject_kind, subject_id);
```

**Aspect Properties:**
- **Temporal**: `valid_from`, `valid_to` (when was it true?), `observed_at` (when did we learn it?)
- **Belief**: Confidence score (0..1)
- **Provenance**: Source metadata (source_id, URI, hash, optional signature)
- **Vector**: Embedding for semantic similarity (multi-space support planned)

---

## Query Layer: CQL

### CQL Parser
Parses queries into structured representation.

**Location:** `cns_py/cql/parser.py`

**Supported Syntax (v0.1):**
```
MATCH label="<string>" [PREDICATE <ident>]
ASOF <iso8601>
BELIEF >= <float>
RETURN [EXPLAIN] [PROVENANCE]
```

**Example:**
```sql
MATCH label="FrameworkX" PREDICATE supports_tls 
ASOF 2025-01-01T00:00:00Z 
BELIEF >= 0.7 
RETURN EXPLAIN PROVENANCE
```

### CQL Executor
Executes parsed queries against the storage layer.

**Location:** `cns_py/cql/executor.py`

**Execution Pipeline:**
1. **ANN Shortlist** (placeholder for Phase 3): Vector similarity search
2. **Temporal Mask**: Apply `ASOF` filter to `valid_from`/`valid_to`
3. **Graph Traverse**: Join atoms ← fibers → atoms with predicate filter
4. **Belief Compute**: Calculate confidence scores
5. **Provenance Enrichment**: Attach source metadata
6. **Result Assembly**: Return atoms + confidence + provenance + explain

**Output Format:**
```json
{
  "results": [
    {
      "subject_label": "FrameworkX",
      "predicate": "supports_tls",
      "object_label": "TLS1.3",
      "confidence": 0.98,
      "provenance": [
        {
          "source_id": "demo_seed:fiber:42",
          "uri": "https://example.org/demo/tls-policy",
          "hash": "demo-sha256-placeholder",
          "fetched_at": "2025-01-10T12:00:00Z"
        }
      ]
    }
  ],
  "explain": {
    "total_ms": 12.5,
    "steps": [
      {"name": "ann_shortlist", "ms": 0.0, "extra": {}},
      {"name": "temporal_mask", "ms": 0.1, "extra": {"asof": "2025-01-01T00:00:00Z"}},
      {"name": "graph_traverse", "ms": 11.2, "extra": {"rows": 1}},
      {"name": "belief_compute", "ms": 1.2, "extra": {"items": 1, "avg_confidence": 0.98}}
    ]
  }
}
```

### CQL Planner
Cost-based query planning (skeleton for Phase 3).

**Location:** `cns_py/cql/planner.py`

**Planned Pipeline:**
1. **ANN Shortlist**: Vector similarity to narrow search space
2. **Temporal Mask**: Filter by `valid_from`/`valid_to`
3. **Graph Expand**: 1-2 hop traversals
4. **Symbolic Verify**: Rule evaluation (WASM sandbox)
5. **Belief Rank**: Order by confidence

---

## Belief System

### Belief Computation
Combines evidence, recency, and source reputation into confidence score.

**Location:** `cns_py/cql/belief.py`

**Formula (v0):**
```python
evidence_score = (base_belief - 0.5) * 6.0  # Map 0..1 to -3..+3
recency_term = 0.5 ** (days_since_observed / half_life_days)
x = w_evidence * evidence_score + w_recency * (recency_term * 2.0 - 1.0)
confidence = sigmoid(x)
```

**Inputs:**
- `base_belief`: Stored belief score (0..1)
- `observed_at`: When we learned about it
- `w_evidence`, `w_recency`: Configurable weights

**Outputs:**
- `confidence`: Final score (0..1)
- `details`: Breakdown for `EXPLAIN` mode

**Future (Phase 4):**
- Source reputation weights
- Contradiction penalties
- Domain-specific belief functions

---

## Contradiction Detection

### Fiber Contradictions
Same subject + predicate pointing to different objects with overlapping temporal validity.

**Location:** `cns_py/cql/contradict.py`

**Example:**
```
FrameworkX --supports_tls--> TLS1.2  (valid: 2020-01-01 to 2025-01-01)
FrameworkX --supports_tls--> TLS1.3  (valid: 2024-12-01 to 2026-01-01)
                                      ^^^^^^^^^^^^^^^^
                                      OVERLAP = CONTRADICTION
```

### Atom Text Contradictions
Same kind + label with different text values during overlapping validity.

**Example:**
```
Atom 1: kind=Entity, label="CompanyX", text="123 Main St"  (valid: 2020-2024)
Atom 2: kind=Entity, label="CompanyX", text="456 Oak Ave"  (valid: 2023-2025)
                                                            ^^^^^^^^
                                                            OVERLAP = CONTRADICTION
```

**Detection:**
- Runs on-demand via `detect_fiber_contradictions()` or `detect_atom_text_contradictions()`
- Returns list of `Contradiction` objects with overlap details
- Future: Scheduled job + real-time detection on insert

---

## Temporal Reasoning

### Bitemporal Model

**Valid Time** (`valid_from`, `valid_to`):
- When was this true **in the world**?
- Example: "FrameworkX supported TLS1.2 from 2020 to 2025"

**Observed Time** (`observed_at`):
- When did **we learn** about it?
- Example: "We discovered this fact on 2024-06-15"

**Why Both?**
- **Valid time**: Answer "What was true on date X?"
- **Observed time**: Answer "What did we know on date Y?"
- **Combined**: Answer "What did we know on date Y about what was true on date X?"

### ASOF Queries

**Syntax:**
```sql
MATCH label="FrameworkX" PREDICATE supports_tls 
ASOF 2024-12-31T23:59:59Z
```

**Semantics:**
```sql
WHERE COALESCE(valid_from, '-infinity') <= '2024-12-31T23:59:59Z'
  AND COALESCE(valid_to, 'infinity') > '2024-12-31T23:59:59Z'
```

**Result:** Returns TLS1.2 (not TLS1.3, which becomes valid 2025-01-01)

---

## Provenance System

### Provenance Structure

```json
{
  "source_id": "rfc9999",
  "uri": "https://datatracker.ietf.org/doc/rfc9999",
  "hash": "sha256:abc123...",
  "fetched_at": "2025-01-10T12:00:00Z",
  "line_span": "42-58",
  "signature": "ed25519:def456..."  // optional
}
```

**Fields:**
- `source_id`: Unique identifier for the source
- `uri`: Where to find the original
- `hash`: Content hash for verification
- `fetched_at`: When we retrieved it
- `line_span`: Optional line numbers in source
- `signature`: Optional Ed25519 signature

### Provenance Chains

Derived claims reference their sources:

```
Original Claim (from RFC):
  Atom: TLS1.3
  Provenance: {source_id: "rfc9999", uri: "https://..."}

Derived Claim (from learner):
  Fiber: FrameworkX --supports_tls--> TLS1.3
  Provenance: {source_id: "learner:tls_extractor:v1", derived_from: ["rfc9999"]}
```

**Verification:**
- Check hash matches content
- Verify signature (if present)
- Trace back to original sources

---

## Tech Stack

### Current (Phase 0-3)
- **Language**: Python 3.10+
- **Database**: PostgreSQL 15+ with pgvector extension
- **Vector Dims**: 384 (configurable via `CNS_VECTOR_DIMS`)
- **Testing**: pytest, hypothesis (property tests), testcontainers
- **Linting**: ruff, black, mypy (strict mode)
- **CI/CD**: GitHub Actions (lint, type, unit, integ, pgTAP, perf)

### Future (Phase 4+)
- **Rust Engine**: Journal (Arrow), graph (CSR + Roaring), vector (IVF-PQ + HNSW)
- **Wire Protocol**: Arrow Flight (data plane), gRPC (control plane)
- **WASM Sandbox**: In-store executable rules and learners
- **Visualization**: React + Three.js (WebGL galaxy map)

---

## Performance Targets

### Phase 1-2 (Python Reference)
- ✅ P95 ≤ 500ms on 10K atoms + 50K fibers (achieved)
- ✅ Coverage ≥ 85% (enforced by CI)

### Phase 3 (Rust Engine Alpha)
- P95 ≤ 150ms on 1M atoms + 5M fibers
- ANN shortlist: 100M vectors (IVF-PQ bulk + HNSW hot set)
- Graph traverse: 1-2 hops with Roaring bitmap masks

### Phase 4 (Production)
- P95 ≤ 50ms on 100M atoms + 1B fibers
- Multi-space vector indexing
- Horizontal scaling (sharding by atom ID ranges)

---

## Scalability Strategy

### Vertical (Single Node)
- **Journal**: Append-only Arrow segments (columnar, compressed)
- **Graph**: CSR (Compressed Sparse Row) + Roaring bitmaps
- **Vector**: IVF-PQ for bulk, HNSW for hot set (RAM cache)
- **Symbolic**: WASM sandbox (lightweight, isolated)

### Horizontal (Multi-Node)
- **Sharding**: By atom ID ranges (consistent hashing)
- **Replication**: Raft consensus for journal writes
- **Caching**: Distributed HNSW cache (Redis/Memcached)
- **Query Routing**: Learned router (classify query → pick shards)

---

## Security Model

### Phase 1-3 (Dev)
- No authentication (local dev only)
- No TLS (localhost connections)
- No row-level security

### Phase 4+ (Production)
- **mTLS**: Between API and DB
- **Signed Provenance**: Ed25519 signatures on claims
- **Row-Level Security**: Capability-based ACLs per atom/fiber
- **Audit Log**: All rule executions logged
- **License Tags**: Enforced in learners (e.g., "no commercial use")

---

## Extension Points

### 1. Custom Belief Functions
Plug in domain-specific confidence calculations.

```python
from cns_py.cql.belief import BeliefConfig

custom_cfg = BeliefConfig(
    w_evidence=1.0,
    w_recency=0.5,
    recency_half_life_days=90.0
)
```

### 2. Custom Learners (Future)
Register WASM modules for in-store learning.

```rust
// Rust WASM learner
#[no_mangle]
pub extern "C" fn entity_resolver(atoms: &[Atom]) -> Vec<Fiber> {
    // Your logic here
}
```

### 3. Custom Embedding Spaces (Future)
Multi-space vector indexing for domain-specific semantics.

```sql
-- Future syntax
CREATE EMBEDDING_SPACE security_protocols DIMS 768;
CREATE EMBEDDING_SPACE legal_documents DIMS 1536;
```

---

## References

- `cns_py/storage/db.py` — Schema and connection management
- `cns_py/cql/parser.py` — CQL parser
- `cns_py/cql/executor.py` — CQL executor
- `cns_py/cql/belief.py` — Belief computation
- `cns_py/cql/contradict.py` — Contradiction detection
- `docs/adr/0001-cql-v0.1-freeze.md` — CQL v0.1 spec
- `docs/05-visualization.md` — IB Explorer design
- `docs/06-ib-vs-db.md` — IB vs DB comparison
