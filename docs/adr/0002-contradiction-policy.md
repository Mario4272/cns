# ADR 0002: Contradiction Detection and Resolution Policy

**Date:** 2025-10-06  
**Status:** Accepted  
**Supersedes:** None

---

## Context

CNS stores intelligence from multiple sources with varying levels of reliability. Contradictions are inevitable and expected, not errors. We need a clear policy for:

1. **Detection**: How do we identify contradictions?
2. **Representation**: How do we store and surface them?
3. **Resolution**: How do we help users resolve conflicts?
4. **Belief Impact**: How do contradictions affect confidence scores?

---

## Decision

### 1. Contradiction Types

We recognize two primary types of contradictions:

#### Type A: Fiber Contradictions
**Definition:** Same subject + predicate pointing to different objects with overlapping temporal validity.

**Example:**
```
FrameworkX --supports_tls--> TLS1.2  (valid: 2020-01-01 to 2025-01-01)
FrameworkX --supports_tls--> TLS1.3  (valid: 2024-12-01 to 2026-01-01)
                                      ^^^^^^^^^^^^^^^^
                                      OVERLAP = CONTRADICTION
```

**Detection SQL:**
```sql
SELECT f1.src, f1.predicate, f1.dst AS obj1, f2.dst AS obj2
FROM fibers f1
JOIN fibers f2 ON f1.src = f2.src AND f1.predicate = f2.predicate AND f1.id < f2.id
JOIN aspects asp1 ON asp1.subject_kind='fiber' AND asp1.subject_id=f1.id
JOIN aspects asp2 ON asp2.subject_kind='fiber' AND asp2.subject_id=f2.id
WHERE f1.dst != f2.dst
  AND asp1.valid_from < asp2.valid_to
  AND asp2.valid_from < asp1.valid_to
```

#### Type B: Atom Text Contradictions
**Definition:** Same kind + label with different text values during overlapping validity.

**Example:**
```
Atom 1: kind=Entity, label="CompanyX", text="123 Main St"  (valid: 2020-2024)
Atom 2: kind=Entity, label="CompanyX", text="456 Oak Ave"  (valid: 2023-2025)
                                                            ^^^^^^^^
                                                            OVERLAP = CONTRADICTION
```

### 2. Detection Policy

**When:**
- On-demand via `detect_fiber_contradictions()` or `detect_atom_text_contradictions()`
- Future: Scheduled background job (Phase 6)
- Future: Real-time on insert (Phase 7)

**Scope:**
- Only detect contradictions with **temporal overlap**
- Non-overlapping claims are supersessions, not contradictions
- Require at least one aspect with temporal bounds

**Filters:**
- Support filtering by subject label, predicate, kind
- Limit results to prevent overwhelming output (default: 100)

### 3. Representation

**Data Structure:**
```python
@dataclass
class Contradiction:
    subject_id: int
    subject_label: str
    predicate: str
    object1_id: int
    object1_label: str
    object2_id: int
    object2_label: str
    overlap_start: Optional[datetime]
    overlap_end: Optional[datetime]
    reason: str  # Human-readable explanation
```

**Storage:**
- No dedicated `contradictions` table (Phase 1-3)
- Computed on-demand from atoms/fibers/aspects
- Future: Materialized view or cache (Phase 4+)

**Visualization:**
- IB Explorer: Lightning arcs between conflicting atoms
- Color: Red/orange for high-severity conflicts
- Animation: Spark/flash effect to draw attention

### 4. Resolution Policy

**User Options:**

#### Option A: Accept One Version (Manual)
User marks one claim as authoritative:
```python
# Future API
resolve_contradiction(
    contradiction_id=42,
    accept=fiber_id_1,
    reject=fiber_id_2,
    reason="Source A is more reliable"
)
```

**Effect:**
- Rejected claim's belief → 0.0
- Accepted claim's belief unchanged or boosted
- Provenance updated with resolution metadata

#### Option B: Temporal Resolution (Automatic)
Use `ASOF` queries to disambiguate:
```sql
-- Query at specific time when only one claim was valid
MATCH label="FrameworkX" PREDICATE supports_tls 
ASOF 2024-06-01T00:00:00Z
RETURN PROVENANCE
```

**Effect:**
- Temporal mask filters out non-overlapping claims
- Returns only claims valid at specified time
- No modification to stored data

#### Option C: Coexistence (Default)
Both claims remain with their original belief scores:
```python
# Query returns both, ordered by belief
results = cql('MATCH label="FrameworkX" PREDICATE supports_tls RETURN')
# results[0] = TLS1.3 (belief: 0.95)
# results[1] = TLS1.2 (belief: 0.90)
```

**Effect:**
- User sees both claims with confidence scores
- Can decide based on provenance, recency, belief
- No data loss

### 5. Belief Impact

**Current (Phase 1-3):**
- Contradictions do **not** automatically reduce belief scores
- Belief is computed from: `base_belief + recency`
- Users see multiple results and choose based on confidence

**Future (Phase 4+):**
- Add contradiction penalty to belief formula:
  ```
  confidence = σ(w_e*evidence + w_r*recency - w_c*contradictions)
  ```
- `w_c` = contradiction weight (default: 0.5)
- Each detected contradiction reduces confidence by `w_c * overlap_ratio`

**Rationale:**
- Phase 1-3: Keep it simple; let users decide
- Phase 4+: Penalize contradictions to surface uncertainty

---

## Consequences

### Positive

1. **Transparency**: Users see conflicting claims, not hidden "resolved" data
2. **Temporal Reasoning**: `ASOF` queries naturally resolve many contradictions
3. **Provenance**: Users can trace back to sources to decide
4. **No Data Loss**: All claims preserved with their original metadata

### Negative

1. **Cognitive Load**: Users must evaluate multiple results
2. **Performance**: Contradiction detection is O(n²) in worst case
3. **Ambiguity**: No single "correct" answer without user input

### Mitigations

1. **Default Ordering**: Return highest-belief result first
2. **Visualization**: Lightning arcs make contradictions obvious
3. **Caching**: Materialize contradiction view for large datasets (Phase 4+)
4. **Heuristics**: Auto-resolve obvious cases (e.g., same source, later timestamp supersedes)

---

## Examples

### Example 1: TLS Version Conflict

**Scenario:**
```
FrameworkX supports TLS1.2 (2020-2025, belief: 0.90, source: doc_v1)
FrameworkX supports TLS1.3 (2024-2026, belief: 0.95, source: doc_v2)
```

**Detection:**
```python
contradictions = detect_fiber_contradictions(
    subject_label="FrameworkX",
    predicate="supports_tls"
)
# Returns 1 contradiction with overlap: 2024-2025
```

**Resolution:**
```sql
-- Option A: Query at specific time
MATCH label="FrameworkX" PREDICATE supports_tls 
ASOF 2024-06-01T00:00:00Z
-- Returns: TLS1.2 (only valid claim at that time)

-- Option B: Get both, ordered by belief
MATCH label="FrameworkX" PREDICATE supports_tls
-- Returns: [TLS1.3 (0.95), TLS1.2 (0.90)]
```

### Example 2: Address Conflict

**Scenario:**
```
CompanyX address = "123 Main St" (2020-2024, belief: 0.85)
CompanyX address = "456 Oak Ave" (2023-2025, belief: 0.90)
```

**Detection:**
```python
contradictions = detect_atom_text_contradictions(
    kind="Entity",
    label="CompanyX"
)
# Returns 1 contradiction with overlap: 2023-2024
```

**Resolution:**
```python
# User manually resolves
resolve_contradiction(
    contradiction_id=42,
    accept=atom_id_2,  # 456 Oak Ave
    reason="Confirmed with company records"
)
```

---

## Future Work (Phase 4+)

1. **Automatic Resolution Heuristics**
   - Same source, later timestamp → supersedes
   - Higher source reputation → wins
   - Majority vote across multiple sources

2. **Contradiction Severity Levels**
   - **Critical**: Core facts (e.g., entity identity)
   - **Warning**: Peripheral facts (e.g., metadata)
   - **Info**: Expected variance (e.g., estimates)

3. **Contradiction Chains**
   - Track resolution history
   - Allow undo/redo
   - Audit trail for compliance

4. **Machine Learning**
   - Train model to predict resolution
   - Active learning: surface uncertain cases
   - Confidence calibration

---

## References

- `cns_py/cql/contradict.py` — Implementation
- `tests/test_contradict.py` — Unit tests
- `tests/test_contradiction_integration.py` — Integration tests
- `docs/02-architecture.md` — Contradiction detection architecture
- `docs/05-visualization.md` — Lightning arc visualization

---

## Approval

**Proposed by:** JR  
**Reviewed by:** Val, Mario  
**Status:** Accepted  
**Date:** 2025-10-06
