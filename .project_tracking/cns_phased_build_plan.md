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

### Makefile targets (to add)
```
make verify       # lint+type+unit+integ+pgTAP+coverage+perf-smoke
make test         # unit + integ
make tap          # pgTAP only
make bench        # criterion + microbench (feature-flagged)
make e2e          # Playwright demo script
```

### Minimal files to add
- `pyproject.toml` (deps + ruff/black/mypy config)
- `tests/` (unit, golden/, property/)
- `tests_pg/` (pgTAP .sql)
- `.devcontainer/devcontainer.json`
- `.github/workflows/ci.yaml`
- `scripts/prov_verify.py` (verify provenance signatures)
- `docs/adr/0001-cql-v0.1-freeze.md`

### Checklist (ACTIVE)
- ☐ Tooling/QA rig (pytest + property tests + testcontainers + coverage)  
  Owner: JR · Labels: `phase/P0A, tests, area/python` · Issue: #9
- ☐ CI workflow (lint, type, unit, integ, pgTAP, coverage, perf-smoke)  
  Owner: JR · Labels: `phase/P0A, tests, docs, perf` · Issue: #10
- ☐ Pre-commit hooks (ruff, black, mypy, detect-secrets)  
  Owner: JR · Labels: `phase/P0A, docs` · Issue: #11
- ☐ Devcontainer for pgvector dev env  
  Owner: JR · Labels: `phase/P0A, docs` · Issue: #12

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
