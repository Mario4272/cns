# CNS Phased Build-Out Plan (IB > DB)

Owner: JR (+ Val/Mario as backseat drivers)  
Goal: Ship a cognition-native substrate that proves value over “just a DB” in 90 days, then harden.

---

## Phase 0 — Bootstrap (Week 0) ✅
**Objective:** Repo + runnable demo to align contributors.

- Repo scaffold (`bootstrap_cns_repo.sh`) with:
  - Python ref impl on Postgres + pgvector.
  - Rust engine skeleton (journal/graph/vector/symbolic/planner crates).
  - Docker pgvector, Makefile, basic docs.
- Demo: TLS 1.2 → TLS 1.3 supersession; `ASOF` query shows change.

**Exit criteria**
- `make up` → `ingest.py` → `query.py` produces expected outputs.
- Docs: 01-vision, 02-architecture, 03-cql-spec-draft, 04-roadmap.

**Evidence (2025-10-04)**
- Demo query results:
  - `As of 2024-12-31T12:00:00+00:00 -> TLS1.2`
  - `As of 2025-01-01T12:00:00+00:00 -> TLS1.3`
- Notes: tightened ASOF filters in `cns_py/demo/query.py` to use `COALESCE(...,'-infinity'/'infinity')` for correctness.

---

## Phase 1 — CQL Surface + Provenance (Weeks 1–3)
**Objective:** Lock a minimal query contract that is *clearly not SQL* and returns citations by default.

### Deliverables
- **CQL v0.1 (subset)**
  - Syntax: `MATCH`, `WHERE SIMILAR()`, `ASOF`, `BELIEF()`, `RETURN … EXPLAIN PROVENANCE`.
  - Parser + executor (Python ref): ANN shortlist → temporal mask → 1–2 hop traverse.
- **Provenance**
  - Every answer returns `[source_id, uri, line_span?, fetched_at, hash]`.
  - `EXPLAIN` includes operator timings and source fanout.
- **Belief economics v0**
  - Logistic update function (weights documented, tunable).
  - Responses include `confidence` per fiber/claim.
- **Tests**
  - Golden tests for `ASOF` differences, citations presence, and belief thresholds.

### Metrics / SLOs
- P95 end-to-end latency ≤ 300 ms on 10k atoms / 100k fibers / 100k vectors (dev box).
- 100% of answers include at least one citation.

### Risks & Mitigations
- *Parser creep* → freeze v0.1 grammar; add features in v0.2 only.
- *Citation gaps* → fail query if no provenance; allow `--allow-hypotheses` to relax.

**Exit criteria**
- `cql(query)` returns results + citations + `EXPLAIN`.
- README shows a CQL example with time-split result + sources.

**Example run (2025-10-04)**
Command:
```
python scripts/cql_smoke.py
```
Excerpt (formatted):
```json
{
  "results": [
    {
      "subject_label": "FrameworkX",
      "predicate": "supports_tls",
      "object_label": "TLS1.3",
      "confidence": 0.98,
      "provenance": [ { "source_id": "fiber:<id>", "uri": null } ]
    }
  ],
  "explain": {
    "steps": [
      { "name": "ann_shortlist", "ms": <n> },
      { "name": "temporal_mask", "ms": <n>, "extra": { "asof": "2025-01-01T00:00:00Z" } },
      { "name": "graph_traverse", "ms": <n>, "extra": { "rows": 1 } }
    ],
    "total_ms": <n>
  }
}
```

---

## Phase 2 — Learners-in-Store (Weeks 3–5)
**Objective:** Make the substrate feel alive: it detects contradictions and resolves entities.

### Deliverables
- **Learner: Entity Resolution v0**
  - Alias → canonical (name similarity + context hints).
  - Writes `ALSO_KNOWN_AS` fibers + canonical IDs.
- **Learner: Contradiction Detector v0**
  - Same `(subject, predicate)`, different `object` → create `CONTRADICTS` edges.
  - Triggers belief arbitration; keep minority view with lower confidence.
- **Belief updater**
  - Incremental recompute on new evidence/contradiction; decay by recency.

### Metrics
- ER precision ≥ 0.9 on curated toy set; contradictions flagged correctly in demo.
- Belief delta visible in `EXPLAIN` (before/after values).

### Risks
- False merges in ER → human-overrides API to split.
- Contradiction spam → throttle by subject/predicate windowing.

**Exit criteria**
- New demo: ingest two conflicting papers → CQL highlights conflict + adjusted beliefs.

---

## Phase 3 — Bundles & Compression (Weeks 5–7)
**Objective:** Keep growth sublinear; speed up queries with graph-aware summaries.

### Deliverables
- **Bundles (semantic compression)**
  - Materialize cluster summaries (centroid claims) with back-pointers.
  - Planner can satisfy broad queries from Bundles, drill to sources on demand.
- **Storage tiering policies**
  - Hot (RAM cache, recent heads), Warm (SSD columnar), Cold (object store).
- **Aging**
  - Recency decay; demote long-tail vectors; keep stubs for rehydration.

### Metrics
- Storage growth with Bundles enabled ≤ 0.5× vs raw ingest.
- Query speedup ≥ 1.5× on cluster-level questions.

**Exit criteria**
- Toggle `use_bundles=true` shows faster results with identical top-k (within tolerance).

---

## Phase 4 — IB Explorer Alpha (Weeks 7–9)
**Objective:** Give users the multi-dimensional feel (IB not DB) and time travel.

### Deliverables
- **WebGL/Three.js Galaxy**
  - Atoms as stars (color by kind), Fibers as edges (thickness by belief).
  - Zoom levels: clusters → subgraphs → atom detail panel (aspects: vector preview, provenance list).
- **Time Slider**
  - Scrub to `ASOF` date; graph hides/shows fibers; belief animates.
- **Contradiction Mode**
  - Pulsing lightning edges between `CONTRADICTS`.

### Metrics
- 60 FPS on 10k nodes/edges on a decent laptop (LOD + instancing).
- “Click atom” panel shows citations and belief history < 100 ms.

**Exit criteria**
- Live demo: switch dates; see TLS claim swap + contradiction animation; click to view sources.

---

## Phase 5 — Rust Engine Alpha (Weeks 9–12)
**Objective:** Stand up the next-gen substrate core without breaking the API.

### Deliverables
- **Journal** (append-only Arrow segments; bitemporal headers; replay).
- **Graph engine v1** (CSR + Roaring masks; 1–2 hop traversals).
- **Vector engine v1** (IVF-PQ bulk; HNSW hot set).
- **Planner v1** (ANN → temporal mask → graph expand; cost heuristics).
- **Wire**: Arrow Flight for result sets; gRPC for control ops.
- **Python SDK** points to Rust engine (feature flag).

### Metrics
- P95 ≤ 150 ms on: ANN shortlist (100M vectors IVF-PQ) → 2-hop traverse → belief filter (RAM HNSW for hot).
- Journal replay produces identical beliefs and contradictions.

**Exit criteria**
- Swap `--engine=rust` for demos; results & citations match Python ref within tolerance.

---

## Phase 6 — Executable Memory + Signed Provenance (Weeks 12–15)
**Objective:** Make the memory executable and auditable.

### Deliverables
- **WASM Sandbox**
  - Register rules/resolvers/summarizers; execute on demand; outputs are Claims with provenance `learner:<hash>`.
- **Signed provenance (optional mode)**
  - Content hashes; Ed25519 signatures on source + derived claims; verification endpoint.

### Metrics
- Rule eval overhead < 30 ms per invocation for small payloads.
- Provenance verify throughput ≥ 10k/s on a single core.

**Exit criteria**
- Demo: run a TLS compliance rule → returns NonCompliant claim with signed provenance chain.

---

## Phase 7 — Learned Routers & Multi-Space (Weeks 15–18)
**Objective:** Increase shortlist quality with domain-specific embedding spaces.

### Deliverables
- Multi-space vector indexing (e.g., `sec_proto`, `legal_v1`, `code_v1`).
- **Router**: classify query → pick space(s) + weights; small adapter training loop.

### Metrics
- Recall@k improves ≥ 10–15% vs single space on mixed-domain benchmark.

**Exit criteria**
- CQL `SIMILAR(x, "text", space="auto")` outperforms fixed space on demo corpus.

---

## Always-On Ops (phases 1–∞)
- **Metrics & Tracing**: OTel spans per operator; Prom counters (ANN, traverse, rule, belief).
- **Backups**: journal snapshots → object store; one-command restore.
- **Security**: capability-based ACLs per cell/fiber/aspect; license tags enforced in learners.
- **CI**: unit + golden tests + perf smoke (ANN P95, traverse P95).

---

## Demos to Ship (Sales/README-ready)
1. **Truth-as-of** (“What did Framework X require on 2024-12-31 vs 2025-09-30?”)  
   - Output: different TLS; `SUPERCEDES` link; citations; `EXPLAIN`.
2. **Contradiction surfacing** (two papers disagree; show lightning edge + belief shift).  
3. **IB Explorer** (galaxy view; time slider; click to see provenance).  
4. **Executable memory** (run a rule; emit a claim; signed provenance).

---

## Acceptance Gate (Go/No-Go to Beta)
- CQL v0.1 stable; tests passing.
- P95 ≤ 150 ms on Rust engine alpha targets.
- 100% answers with citations; `EXPLAIN` readable.
- IB Explorer demo smooth at 10k nodes.
- Journal snapshot/replay proven identical.

---

## Issue Backlog (initial)
- CQL grammar: edge labels, qualifiers, limit/order, pagination.
- Planner: better cost model (mask selectivity; fanout estimates).
- Belief: domain weights; source reputation model.
- ER: add embedding-based and graph-based features.
- Bundles: parameterize size/coverage; auto-demotion heuristics.
- Flight integration: columnar result frames; zero-copy to frontend.
- Security: signed provenance toggle; export scrubber (license-aware).
  208→- Visualization: saved layouts; provenance color filters; “why/why-not” overlays.
  209→
  210→
---

# Global Contracts

### 1. Citations Contract
- Every answer must include citations for claims: `[source_id, uri, hash, optional line_span, fetched_at]`.
- If no citations are available, the engine should return an empty result (no hallucinations).
- CQL flag: `REQUIRE PROVENANCE` (default true).

### 2. Belief Math Contract
- Default, configurable belief function:
  - `confidence = σ(w_e*evidence + w_r*source_rep + w_t*recency − w_c*contradictions)`
- `EXPLAIN` must show before/after confidence deltas and per-term breakdown.

### 3. Time/ASOF Contract
- All traversals are bitemporal; `ASOF <ts>` applies a temporal mask to atoms/fibers.

### 4. Hypothesis vs Claim
- Claim requires provenance and is returned by default.
- Hypothesis mode (off by default) can surface unproven suggestions; must be clearly labeled and carry separate priors.
