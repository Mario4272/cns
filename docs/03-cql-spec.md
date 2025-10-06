# CQL Specification v0.1

**CQL** = **Cognition Query Language**

A query language for intelligence bases that blends similarity, structure, time, and belief.

---

## Design Principles

1. **Declarative**: Specify what you want, not how to get it
2. **Temporal-first**: Time is native, not bolted on
3. **Probabilistic**: Results have confidence scores, not binary truth
4. **Provenance-aware**: Every result includes citations
5. **Explainable**: `EXPLAIN` shows reasoning for every query

---

## Grammar (v0.1)

### Minimal Syntax

```ebnf
query       ::= MATCH clause [ASOF clause] [BELIEF clause] RETURN clause
MATCH       ::= "MATCH" label_clause [predicate_clause]
label_clause ::= "label=" QUOTED_STRING
predicate_clause ::= "PREDICATE" IDENTIFIER
ASOF        ::= "ASOF" ISO8601_TIMESTAMP
BELIEF      ::= "BELIEF" ">=" FLOAT
RETURN      ::= "RETURN" [EXPLAIN] [PROVENANCE]
EXPLAIN     ::= "EXPLAIN"
PROVENANCE  ::= "PROVENANCE"
```

### Tokens

- `QUOTED_STRING`: `"FrameworkX"`, `"TLS1.3"`
- `IDENTIFIER`: `supports_tls`, `requires`, `knows`
- `ISO8601_TIMESTAMP`: `2025-01-01T00:00:00Z`, `2024-12-31T23:59:59Z`
- `FLOAT`: `0.7`, `0.95`, `1.0`

---

## Clauses

### MATCH

Specifies the pattern to search for.

**Syntax:**
```sql
MATCH label="<atom_label>" [PREDICATE <relation_type>]
```

**Examples:**
```sql
-- Find all fibers from FrameworkX
MATCH label="FrameworkX"

-- Find all "supports_tls" fibers from FrameworkX
MATCH label="FrameworkX" PREDICATE supports_tls
```

**Semantics:**
- `label="X"`: Filter source atoms by label
- `PREDICATE p`: Filter fibers by predicate type
- Returns: Subject atom, predicate, object atom

### ASOF

Temporal filter: "as of this point in time".

**Syntax:**
```sql
ASOF <iso8601_timestamp>
```

**Examples:**
```sql
-- What was true on 2024-12-31?
MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2024-12-31T23:59:59Z

-- What was true on 2025-01-01?
MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T00:00:00Z
```

**Semantics:**
```sql
WHERE COALESCE(aspects.valid_from, '-infinity'::timestamptz) <= <timestamp>
  AND COALESCE(aspects.valid_to,   'infinity'::timestamptz)  >  <timestamp>
```

**Behavior:**
- Filters atoms/fibers by their `valid_from`/`valid_to` range
- Returns only those valid at the specified timestamp
- If omitted, returns all (no temporal filter)

### BELIEF

Confidence threshold filter.

**Syntax:**
```sql
BELIEF >= <float>
```

**Examples:**
```sql
-- Only high-confidence results
MATCH label="FrameworkX" BELIEF >= 0.9

-- Medium confidence or higher
MATCH label="FrameworkX" BELIEF >= 0.5
```

**Semantics:**
```sql
WHERE COALESCE(aspects.belief, 0.0) >= <threshold>
```

**Behavior:**
- Filters results by computed confidence score
- Confidence is calculated by belief function (see `cns_py/cql/belief.py`)
- If omitted, returns all (no belief filter)

### RETURN

Specifies what to return and optional metadata.

**Syntax:**
```sql
RETURN [EXPLAIN] [PROVENANCE]
```

**Flags:**
- `EXPLAIN`: Include query execution plan and timings
- `PROVENANCE`: Include source citations (default: true in v0.1)

**Examples:**
```sql
-- Minimal: just results
MATCH label="FrameworkX" RETURN

-- With explanation
MATCH label="FrameworkX" RETURN EXPLAIN

-- With provenance (default)
MATCH label="FrameworkX" RETURN PROVENANCE

-- Both
MATCH label="FrameworkX" RETURN EXPLAIN PROVENANCE
```

---

## Result Format

### Structure

```json
{
  "results": [
    {
      "subject_label": "<source_atom_label>",
      "predicate": "<fiber_predicate>",
      "object_label": "<destination_atom_label>",
      "confidence": <float>,
      "provenance": [
        {
          "source_id": "<string>",
          "uri": "<string>",
          "hash": "<string>",
          "fetched_at": "<iso8601>",
          "line_span": "<string>"
        }
      ]
    }
  ],
  "explain": {
    "total_ms": <float>,
    "steps": [
      {
        "name": "<step_name>",
        "ms": <float>,
        "extra": { ... }
      }
    ]
  }
}
```

### Fields

**results[]**:
- `subject_label`: Source atom label
- `predicate`: Fiber relation type
- `object_label`: Destination atom label
- `confidence`: Computed belief score (0..1)
- `provenance[]`: List of source citations

**explain** (if `RETURN EXPLAIN`):
- `total_ms`: Total query execution time
- `steps[]`: Per-operator breakdown
  - `name`: Operator name (e.g., "ann_shortlist", "temporal_mask", "graph_traverse")
  - `ms`: Time spent in this operator
  - `extra`: Operator-specific metadata

---

## Examples

### Example 1: Basic Query

**Query:**
```sql
MATCH label="FrameworkX" PREDICATE supports_tls RETURN PROVENANCE
```

**Result:**
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
          "fetched_at": "2025-01-10T12:00:00Z",
          "line_span": null
        }
      ]
    }
  ]
}
```

### Example 2: Temporal Query

**Query:**
```sql
MATCH label="FrameworkX" PREDICATE supports_tls 
ASOF 2024-12-31T23:59:59Z 
RETURN EXPLAIN PROVENANCE
```

**Result:**
```json
{
  "results": [
    {
      "subject_label": "FrameworkX",
      "predicate": "supports_tls",
      "object_label": "TLS1.2",
      "confidence": 0.95,
      "provenance": [...]
    }
  ],
  "explain": {
    "total_ms": 12.5,
    "steps": [
      {"name": "ann_shortlist", "ms": 0.0, "extra": {}},
      {"name": "temporal_mask", "ms": 0.1, "extra": {"asof": "2024-12-31T23:59:59Z"}},
      {"name": "graph_traverse", "ms": 11.2, "extra": {"rows": 1}},
      {"name": "belief_compute", "ms": 1.2, "extra": {"items": 1}}
    ]
  }
}
```

**Note:** Returns TLS1.2 (not TLS1.3) because TLS1.3 becomes valid on 2025-01-01.

### Example 3: Belief Threshold

**Query:**
```sql
MATCH label="FrameworkX" BELIEF >= 0.97 RETURN PROVENANCE
```

**Result:**
```json
{
  "results": [
    {
      "subject_label": "FrameworkX",
      "predicate": "supports_tls",
      "object_label": "TLS1.3",
      "confidence": 0.98,
      "provenance": [...]
    }
  ]
}
```

**Note:** Only returns TLS1.3 (0.98) because TLS1.2 (0.95) is below threshold.

---

## Execution Pipeline

### Phase 1: Parse
```
Query String → Parser → CqlQuery Object
```

**Parser:** `cns_py/cql/parser.py`

### Phase 2: Plan
```
CqlQuery → Planner → Execution Plan
```

**Planner:** `cns_py/cql/planner.py` (skeleton in v0.1)

**Planned Pipeline:**
1. ANN shortlist (vector similarity)
2. Temporal mask (ASOF filter)
3. Graph expand (traverse fibers)
4. Symbolic verify (rule evaluation)
5. Belief rank (order by confidence)

### Phase 3: Execute
```
Execution Plan → Executor → Results + Explain
```

**Executor:** `cns_py/cql/executor.py`

**Current Pipeline (v0.1):**
1. **ANN Shortlist**: Placeholder (0ms, returns None)
2. **Temporal Mask**: Apply ASOF bounds
3. **Graph Traverse**: SQL join on atoms ← fibers → atoms
4. **Belief Compute**: Calculate confidence scores
5. **Provenance Enrichment**: Attach source metadata
6. **Result Assembly**: Format as JSON

---

## Contracts

### 1. Citations Contract

**Rule:** Every answer must include citations.

**Enforcement:**
- Every result has `provenance[]` array
- If no provenance available, return empty results (no hallucinations)
- CQL flag: `REQUIRE PROVENANCE` (default: true)

**Example:**
```json
{
  "results": [
    {
      "subject_label": "FrameworkX",
      "provenance": [
        {"source_id": "rfc9999", "uri": "https://..."}
      ]
    }
  ]
}
```

### 2. Belief Math Contract

**Formula (v0.1):**
```
confidence = σ(w_e*evidence + w_r*recency)
```

**Defaults:**
- `w_e = 1.0` (evidence weight)
- `w_r = 0.25` (recency weight)
- `recency_half_life = 365 days`

**Future (v0.2+):**
```
confidence = σ(w_e*evidence + w_r*source_rep + w_t*recency - w_c*contradictions)
```

**EXPLAIN Output:**
```json
{
  "belief_details": {
    "base_belief": 0.95,
    "evidence_score": 2.7,
    "recency": 0.98,
    "weights": {"w_evidence": 1.0, "w_recency": 0.25},
    "logit": 2.945
  }
}
```

### 3. Time/ASOF Contract

**Rule:** All traversals are bitemporal.

**Semantics:**
- `ASOF <ts>` applies temporal mask to atoms/fibers
- Mask: `valid_from <= ts < valid_to`
- If `valid_from` is NULL, treat as `-infinity`
- If `valid_to` is NULL, treat as `+infinity`

**SQL Translation:**
```sql
WHERE COALESCE(aspects.valid_from, '-infinity'::timestamptz) <= :ts
  AND COALESCE(aspects.valid_to,   'infinity'::timestamptz)  >  :ts
```

### 4. Hypothesis vs Claim

**Claim** (default):
- Requires provenance
- Returned by default
- High confidence threshold

**Hypothesis** (future):
- Optional mode (off by default)
- Can surface unproven suggestions
- Must be clearly labeled
- Separate priors

---

## Future Extensions (v0.2+)

### 1. Multi-Hop Patterns

```sql
-- Future syntax
MATCH (a:Entity)-[:knows]->(b:Person)-[:works_at]->(c:Company)
WHERE a.label = "Alice"
RETURN a, b, c
```

### 2. Similarity Search

```sql
-- Future syntax
MATCH (e:Entity)
WHERE SIMILAR(e.vector, embed("security framework")) > 0.75
RETURN e
```

### 3. Aggregations

```sql
-- Future syntax
MATCH (e:Entity)-[:located_in]->(c:City)
RETURN c.label, COUNT(e) AS entity_count
ORDER BY entity_count DESC
```

### 4. Contradiction Queries

```sql
-- Future syntax
MATCH CONTRADICTIONS
WHERE subject.label = "FrameworkX"
RETURN subject, object1, object2, overlap_period
```

### 5. Rule Execution

```sql
-- Future syntax
RULE likely_duplicate(p1, p2) :-
  label(p1) = 'person' AND label(p2) = 'person'
  AND SIMILAR(p1.vector, p2.vector) > 0.92;

EXECUTE RULE likely_duplicate RETURN PROVENANCE;
```

---

## Non-Goals (v0.1)

The following are explicitly **out of scope** for v0.1:

- ❌ Multi-hop path patterns
- ❌ Complex WHERE clauses
- ❌ JOINs beyond single fiber traversal
- ❌ Planner cost model (beyond basic pipeline)
- ❌ Pagination/ordering (beyond default belief ordering)
- ❌ Aggregations (COUNT, SUM, AVG)
- ❌ User-defined functions
- ❌ Subqueries
- ❌ Transactions (all queries are read-only)

---

## Implementation Status

### ✅ Implemented (v0.1)
- Parser for MATCH, ASOF, BELIEF, RETURN
- Executor with temporal mask + graph traverse
- Belief computation (sigmoid + recency)
- Provenance enrichment
- EXPLAIN mode
- Golden tests (4 test cases)

### 🔄 In Progress
- Planner cost model
- ANN shortlist (vector similarity)

### 📋 Planned (v0.2+)
- Multi-hop patterns
- Similarity search
- Aggregations
- Contradiction queries
- Rule execution

---

## References

- **ADR 0001**: CQL v0.1 Grammar Freeze (`docs/adr/0001-cql-v0.1-freeze.md`)
- **Parser**: `cns_py/cql/parser.py`
- **Executor**: `cns_py/cql/executor.py`
- **Planner**: `cns_py/cql/planner.py`
- **Belief**: `cns_py/cql/belief.py`
- **Tests**: `tests/test_parser.py`, `tests/test_cql_executor.py`
- **Golden Tests**: `tests/golden/*.json`

---

## Version History

- **v0.1** (2025-10-04): Initial freeze
  - MATCH label + predicate
  - ASOF temporal filter
  - BELIEF threshold
  - RETURN EXPLAIN PROVENANCE
  - Frozen via ADR 0001
