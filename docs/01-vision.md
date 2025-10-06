# CNS Vision: Intelligence Base > Database

## Core Premise

**CNS = Cognition-Native Store**

Not a database. A **substrate for intelligence**.

Where databases store **data**, CNS stores **intelligence**: atoms (facts, entities, rules, programs) and fibers (relations) with aspects (vector, symbolic, provenance, belief, temporal).

---

## The Problem with Databases

Traditional databases (relational, document, graph, vector) were designed for the era of **data scarcity** (1970s-2000s):

- **Normalize to save space** — Storage was expensive
- **Exact queries for precise retrieval** — Data was clean and certain
- **Single source of truth** — Contradictions were errors, not features
- **Time is an afterthought** — Timestamps are just another column
- **Learning happens outside** — ETL pipelines, external ML models

This worked when:
- Data was scarce and expensive to store
- Sources were few and authoritative
- Contradictions were rare
- Temporal reasoning was simple

---

## The Reality of Modern Intelligence Work

Today's world is different:

### Data Abundance
- Petabytes of data from thousands of sources
- Redundancy is unavoidable
- Contradictions are expected, not exceptional

### Uncertainty is Normal
- Multiple conflicting sources
- Varying levels of reliability
- Confidence scores, not binary truth

### Time is Critical
- Valid time (when was it true in the world?)
- Observed time (when did we learn about it?)
- Bitemporal reasoning is essential

### Provenance Matters
- Where did this come from?
- Who said it?
- Can we verify it?
- What's the chain of evidence?

### Learning is Continuous
- Entity resolution (which records are the same?)
- Contradiction detection (what conflicts?)
- Belief updates (how confident are we?)
- Summarization (what's the essence?)

---

## The CNS Solution: Intelligence Base

CNS is designed for the era of **data abundance** (2020s+):

### 1. Intelligence as First-Class Primitive

**Atoms** — Not rows, but intelligence units:
- **Entities**: People, organizations, systems
- **Concepts**: Protocols, standards, ideas
- **Rules**: Logic, constraints, policies
- **Programs**: Executable code, learners

**Fibers** — Not foreign keys, but typed relations:
- Temporal validity (`valid_from`, `valid_to`)
- Belief scores (0..1 confidence)
- Provenance chains (signed sources)

**Aspects** — Co-resident properties:
- `vector[]` — Multi-space semantics
- `symbol` — AST / Datalog / SMT terms
- `text` — Canonical and free-form
- `belief` — Confidence, evidence, contradictions
- `provenance` — Signed source chains
- `tape` — Bitemporal time

### 2. Queries Blend Similarity + Structure + Time

**CQL (Cognition Query Language)** combines:
- Vector similarity (semantic search)
- Graph traversal (structural relationships)
- Temporal logic (time travel)
- Symbolic reasoning (rule evaluation)

Every result includes:
- **Confidence score** (how certain?)
- **Provenance** (from where?)
- **Explanation** (why this result?)

### 3. Contradictions are Features, Not Bugs

- Multiple conflicting claims can coexist
- Contradictions are surfaced automatically
- Belief scores help rank competing claims
- Time travel shows when contradictions emerged

### 4. Learning Happens Inside the Store

**In-store learners**:
- **Entity resolution**: Merge duplicates → `same_as` fibers
- **Contradiction detection**: Surface conflicts automatically
- **Belief updates**: Recompute confidence as evidence arrives
- **Summarization**: Compress neighborhoods into summary atoms
- **Executable rules**: WASM sandbox for in-store programs

### 5. Provenance is Built-In

- Every claim carries source metadata
- Optional signed provenance (Ed25519)
- Derived claims trace back to originals
- Verification happens at query time

---

## Long-Term Vision: From DB to IB

### Phase 1: Prove the Concept (Months 0-6)
- Python reference implementation
- CQL v0.1 (minimal but complete)
- Demo: Temporal reasoning + contradiction detection
- Visualization: Galaxy map (atoms as stars, fibers as edges)

### Phase 2: Scale the Substrate (Months 6-12)
- Rust engine (journal, graph, vector, symbolic)
- 100M+ atoms, 1B+ fibers
- P95 latency ≤ 150ms
- Multi-space vector indexing

### Phase 3: Intelligence Operations (Months 12-18)
- Continuous learning (ER, contradiction, belief)
- Executable memory (WASM rules)
- Signed provenance chains
- Multi-user collaboration

### Phase 4: Beyond Database (Months 18-24)
- XR visualization (walk through your IB in VR)
- Multi-dimensional navigation
- Cognitive cartography
- Industry adoption

---

## Why This Matters

### For Developers
- **Less glue code**: One substrate instead of vector DB + graph DB + temporal DB
- **Fewer pipelines**: Learning happens in-store
- **Better debugging**: `EXPLAIN` shows reasoning
- **Provenance by default**: Every answer has citations

### For Data Scientists
- **Unified substrate**: Train and query on same store
- **Temporal ML**: Native time-aware features
- **Explainability**: Belief scores + provenance = interpretable
- **Active learning**: Contradictions surface labeling needs

### For Analysts
- **Time travel**: "What did we know on date X?"
- **Contradiction surfacing**: Find conflicts automatically
- **Source tracking**: Filter by reliability
- **Semantic search**: Find similar without exact keywords

### For Compliance/Audit
- **Immutable provenance**: Signed chains prove lineage
- **Temporal audit**: Reconstruct any point in time
- **Contradiction reports**: Identify conflicting requirements
- **Explain mode**: Show reasoning for every decision

---

## Guiding Principles

### 1. Intelligence > Data
Think atoms and fibers, not rows and tables. Think beliefs and contradictions, not constraints and errors.

### 2. Uncertainty is Normal
Embrace probabilistic reasoning. Multiple claims with different confidence scores are the default, not the exception.

### 3. Time is Native
Bitemporal reasoning (valid time + observed time) is built-in, not bolted on.

### 4. Provenance is Mandatory
Every claim must trace back to sources. No hallucinations. Citations are first-class.

### 5. Learning is Continuous
Entity resolution, contradiction detection, belief updates happen inside the store, not in external pipelines.

### 6. Visualization Matters
Intelligence is multi-dimensional. Galaxy maps, time sliders, and contradiction lightning make it tangible.

---

## Success Criteria

CNS succeeds when:

1. **Developers prefer it** over stitching together vector DB + graph DB + temporal DB
2. **Data scientists trust it** for both training and serving
3. **Analysts use it daily** for temporal reasoning and contradiction surfacing
4. **Compliance teams rely on it** for provenance and audit trails
5. **The industry recognizes** "IB" as a category distinct from "DB"

---

## The Shift: DB → IB

| Aspect | Database (DB) | Intelligence Base (IB) |
|--------|---------------|------------------------|
| **Stores** | Data | Intelligence |
| **Primitive** | Row/Document/Node | Atom (entity/fact/rule/program) |
| **Truth** | Single version | Multiple claims with belief |
| **Contradiction** | Error | Feature |
| **Time** | Column | Native bitemporal |
| **Provenance** | External audit log | Built-in signed chains |
| **Query** | Exact match | Similarity + structure + time |
| **Learning** | External (ETL) | Internal (in-store) |
| **Visualization** | Tables/charts | Galaxy map (atoms=stars) |

---

## Conclusion

CNS is not a better database. It's a **different substrate** for a different era.

If you're storing **data**, use a database.  
If you're storing **intelligence**, use CNS.

**Welcome to the Intelligence Base era.**
