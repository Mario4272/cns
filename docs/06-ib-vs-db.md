# IB vs DB: Why CNS is Not a Database

## The Fundamental Shift

**Databases (DBs)** store data.  
**Intelligence Bases (IBs)** store intelligence.

This isn't just marketing. It's a different computational substrate with different primitives, different query semantics, and different guarantees.

---

## What Makes a DB a DB?

Traditional databases (relational, document, graph, vector) share common assumptions:

### 1. **Data is Ground Truth**
- What you write is what you get
- No inherent uncertainty or belief
- Contradictions are errors, not features
- Single version of truth (or explicit versioning)

### 2. **Queries are Exact**
- SQL: `WHERE age > 30` returns exact matches
- Graph: `MATCH (a)-[:KNOWS]->(b)` follows explicit edges
- Vector: `ORDER BY distance` ranks by metric, no reasoning

### 3. **Time is an Afterthought**
- Timestamps are just another column
- Temporal queries require manual range filters
- No native bitemporal support (valid time vs observed time)
- Snapshots are application-level concerns

### 4. **Provenance is External**
- Audit logs are separate tables
- No signed chains of evidence
- Trust is implicit (data is assumed correct)
- Citations are application-level metadata

### 5. **Learning is Outside**
- ETL pipelines preprocess data before insert
- ML models train on exported data
- Entity resolution happens in application code
- Contradiction detection is a separate service

---

## What Makes CNS an IB?

CNS inverts these assumptions to create a substrate for **intelligence**, not just data.

### 1. **Intelligence is Probabilistic**
- Every atom/fiber has a **belief** score (0..1)
- Contradictions are **first-class citizens**, not errors
- Multiple conflicting claims can coexist with different beliefs
- Belief updates as new evidence arrives

**Example:**
```sql
-- DB: Only one value can be true
UPDATE config SET tls_version = 'TLS1.3' WHERE framework = 'X';

-- IB: Multiple claims with belief scores
ASSERT (FrameworkX, supports_tls, TLS1.2) BELIEF 0.95 VALID_UNTIL 2025-01-01;
ASSERT (FrameworkX, supports_tls, TLS1.3) BELIEF 0.98 VALID_FROM 2025-01-01;
-- Both coexist; queries return highest-belief match for given time
```

### 2. **Queries Blend Similarity + Structure + Time**
- CQL combines vector similarity, graph traversal, and temporal logic
- Results ranked by belief, not just distance or exact match
- Queries return **explanations** (why this result?) and **provenance** (from where?)

**Example:**
```sql
-- DB: Exact match only
SELECT * FROM entities WHERE name = 'Alex Jensen';

-- IB: Semantic + structural + temporal
MATCH (p:person)
WHERE SIMILAR(p.vector, embed("Alex from Jensen-verse")) > 0.75
  AND ASOF '2024-06-01'
  AND BELIEF(p) >= 0.8
RETURN p, EXPLAIN, PROVENANCE;
-- Returns similar entities with confidence scores and citations
```

### 3. **Time is Native (Bitemporal)**
- Every atom/fiber has `valid_from`, `valid_to` (when it was true in the world)
- Every aspect has `observed_at` (when we learned about it)
- `ASOF` queries are first-class, not hacks
- Time travel is built-in, not bolted on

**Example:**
```sql
-- DB: Manual temporal logic
SELECT * FROM facts 
WHERE entity_id = 123 
  AND valid_from <= '2024-12-31' 
  AND (valid_to IS NULL OR valid_to > '2024-12-31');

-- IB: Native temporal semantics
MATCH (e:Entity {label: "FrameworkX"})-[r]->(v)
ASOF '2024-12-31'
RETURN e, r, v;
-- Temporal mask applied automatically to all atoms/fibers
```

### 4. **Provenance is Built-In**
- Every claim carries **provenance**: source, URI, hash, fetched_at
- Optional **signed provenance** with Ed25519 signatures
- Queries can filter/rank by source reliability
- Derived claims trace back to original evidence

**Example:**
```sql
-- DB: Provenance is application metadata
INSERT INTO facts (claim, source_url) VALUES ('X supports TLS1.3', 'https://...');

-- IB: Provenance is substrate-level
ASSERT (FrameworkX, supports_tls, TLS1.3)
  PROVENANCE {
    source_id: "rfc9999",
    uri: "https://datatracker.ietf.org/doc/rfc9999",
    hash: "sha256:abc123...",
    signature: "ed25519:def456...",
    fetched_at: "2025-01-10T12:00:00Z"
  };
-- Provenance returned with every query result
```

### 5. **Learning Happens Inside**
- **Entity resolution**: Runs in-store, creates `same_as` fibers
- **Contradiction detection**: Automatic, surfaces conflicts
- **Belief updates**: Scheduled jobs recompute confidence
- **Summarization**: Compress neighborhoods into summary atoms
- **Executable rules**: WASM sandbox for in-store programs

**Example:**
```sql
-- DB: Entity resolution is external ETL
-- (Python script merges duplicates, updates foreign keys)

-- IB: Entity resolution is in-store
RULE likely_duplicate(p1, p2) :-
  label(p1) = 'person' AND label(p2) = 'person'
  AND SIMILAR(p1.vector, p2.vector) > 0.92
  AND text_overlap(p1.text, p2.text) > 0.8;

-- Learner runs periodically, creates same_as fibers with provenance
```

---

## Side-by-Side Comparison

| Aspect | Database (DB) | Intelligence Base (IB) |
|--------|---------------|------------------------|
| **Primitive** | Row, Document, Node | Atom (entity/fact/rule/program) |
| **Relation** | Foreign key, Edge | Fiber (typed, temporal, belief-scored) |
| **Truth** | Single version | Multiple claims with belief |
| **Contradiction** | Error (constraint violation) | Feature (lightning arc in viz) |
| **Time** | Column (manual logic) | Native bitemporal (valid + observed) |
| **Provenance** | External audit log | Built-in signed chains |
| **Query** | Exact match (SQL/Cypher) | Similarity + structure + time (CQL) |
| **Result** | Rows/documents | Atoms + belief + provenance + explain |
| **Learning** | External (ETL, ML pipelines) | Internal (ER, contradiction, belief) |
| **Uncertainty** | Not modeled | First-class (belief scores) |
| **Visualization** | Tables, charts | Galaxy map (atoms=stars, fibers=edges) |

---

## Why This Matters

### For Developers
- **Less glue code**: No separate vector DB + graph DB + temporal DB
- **Fewer pipelines**: Learning happens in-store, not in external jobs
- **Better debugging**: `EXPLAIN` shows why a result was returned
- **Provenance by default**: Every answer comes with citations

### For Data Scientists
- **Unified substrate**: Train models on same store that serves queries
- **Temporal ML**: Native support for time-aware features
- **Explainability**: Belief scores + provenance chains = interpretable results
- **Active learning**: Contradictions surface labeling opportunities

### For Analysts
- **Time travel**: Answer "what did we know on date X?" without snapshots
- **Contradiction surfacing**: Automatically find conflicting claims
- **Source tracking**: Filter by reliability, trace back to original docs
- **Semantic search**: Find similar entities without exact keyword matches

### For Compliance/Audit
- **Immutable provenance**: Signed chains prove data lineage
- **Temporal audit**: Reconstruct state at any point in time
- **Contradiction reports**: Identify conflicting regulatory requirements
- **Explain mode**: Show reasoning for every decision

---

## When to Use a DB vs IB

### Use a Traditional Database When:
- ✅ Data is certain and exact (e.g., financial transactions)
- ✅ Schema is stable and well-defined
- ✅ Queries are exact-match or simple aggregations
- ✅ No temporal complexity (or simple timestamps suffice)
- ✅ Provenance is not critical
- ✅ No contradictions expected (or they're errors)

### Use an Intelligence Base When:
- ✅ Data is uncertain or from multiple conflicting sources
- ✅ Schema evolves (new entity types, relations discovered)
- ✅ Queries blend similarity, structure, and time
- ✅ Temporal reasoning is core (valid time vs observed time)
- ✅ Provenance and citations are required
- ✅ Contradictions are expected and need surfacing
- ✅ Learning (ER, summarization, belief updates) happens continuously

---

## Migration Path: DB → IB

You don't have to replace your DB. CNS can **augment** it.

### Hybrid Architecture
```
┌─────────────────┐
│  Postgres/MySQL │  ← Transactional data (orders, payments)
│  (DB)           │
└────────┬────────┘
         │ ETL
         ↓
┌─────────────────┐
│  CNS (IB)       │  ← Intelligence layer (entities, relations, beliefs)
│                 │     - Entity resolution
│                 │     - Contradiction detection
│                 │     - Temporal reasoning
│                 │     - Provenance tracking
└─────────────────┘
```

### Example Use Cases
1. **Customer 360**: DB stores transactions; IB resolves entities, tracks relationships
2. **Compliance**: DB stores policies; IB detects contradictions, tracks changes over time
3. **Security**: DB stores logs; IB builds attack graphs, surfaces anomalies
4. **Research**: DB stores papers; IB extracts claims, detects conflicts, tracks citations

---

## The Long-Term Vision

**Databases** were designed for the era of **data scarcity** (1970s-2000s):
- Normalize to save space
- Exact queries for precise retrieval
- Single source of truth

**Intelligence Bases** are designed for the era of **data abundance** (2020s+):
- Embrace redundancy and contradiction
- Probabilistic queries for uncertain data
- Multiple sources with belief scores
- Learning as a first-class operation

CNS is the first step toward this future. Not a better database. A different substrate entirely.

---

## Further Reading

- `docs/01-vision.md` (coming soon) — CNS philosophy and goals
- `docs/02-architecture.md` (coming soon) — Technical deep dive
- `docs/03-cql-spec.md` (coming soon) — CQL language reference
- `docs/05-visualization.md` — IB Explorer (galaxy map UI)
- `.project_tracking/cns_project_overview.md` — Roadmap and status

---

**Bottom line:**  
If you're storing **data**, use a database.  
If you're storing **intelligence**, use CNS.
