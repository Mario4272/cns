# CNS Phased Build-Out Plan (IB > DB)

Owner: JR (+ Val/Mario as backseat drivers)  
Goal: Ship a cognition-native substrate that proves value over “just a DB” in 90 days, then harden.

## Project Overview

Short orientation and pointers to canonical docs:

- Vision: see `docs/01-vision.md`.
- Architecture: see `docs/02-architecture.md`.
- Architecture: see `docs/02-architecture.md`.
- Roadmap: this document is the single source of truth.

> [!NOTE]
> This file is tracked in `.project_tracking/cns_phased_build_plan.md`.


## Phase 0 — Bootstrap (Week 0) ✅ COMPLETE

**Objective:** Repo + runnable demo to align contributors.

- ✅ Repo scaffold (`bootstrap_cns_repo.sh`) with:
  - ✅ Python ref impl on Postgres + pgvector.
  - ⚠️ Rust engine skeleton (deferred to Phase 5).
  - ✅ Docker pgvector, Makefile, basic docs.
- ✅ Demo: TLS 1.2 → TLS 1.3 supersession; `ASOF` query shows change.

**Exit criteria**

- ✅ `make up` → `ingest.py` → `query.py` produces expected outputs.
- ⚠️ Docs: 01-vision, 02-architecture, 03-cql-spec-draft, 04-roadmap (content exists in tracking docs, needs extraction).

**Status (2025-10-06)**

- ✅ Demo working end-to-end
- ✅ All core functionality implemented
- ⚠️ Documentation needs reorganization (not blocking)

**Status (2025-11-13)**

- ✅ Mypy CI failures fixed (executor provenance Optional handling guarded)
- ✅ CI pipeline unblocked; coverage gate temporarily set to 75%
- 🔜 Add tests (executor provenance, nn search, DB isolation) to restore gate to 85%

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

### Phase 0A Checklist ✅ COMPLETE

- ✅ Tooling/QA rig (pytest + property tests + testcontainers + coverage)  
  Owner: JR · Labels: `phase/P0A, tests, area/python` · Issue: #9
- ✅ CI workflow (lint, type, unit, integ, pgTAP, coverage, perf-smoke)  
  Owner: JR · Labels: `phase/P0A, tests, docs, perf` · Issue: #10
- ✅ Pre-commit hooks (ruff, black, mypy, detect-secrets)  
  Owner: JR · Labels: `phase/P0A, docs` · Issue: #11
- ✅ Devcontainer for pgvector dev env  
  Owner: JR · Labels: `phase/P0A, docs` · Issue: #12

---

## Phase 1 — Python Reference (Weeks 1-2) ✅ COMPLETE

**Objective:** Prove core concepts with Python + Postgres.

### Deliverables

- ✅ Schema: atoms, fibers, aspects (belief, vectors, temporal)
- ✅ Core API: `upsert_atom`, `link_with_validity`
- ✅ Demo: TLS 1.2 → TLS 1.3 supersession with temporal queries
- ✅ Basic temporal queries (`ASOF`)

**Status (2025-10-06)**

- ✅ All deliverables complete
- ✅ Demo working end-to-end
- ⚠️ Full API layer (`nn_search`, `traverse_from`) deferred to Phase 3

---

## Phase 2 — CQL Draft (Weeks 2-3) ✅ COMPLETE

**Objective:** Minimal CQL parser + executor.

### Deliverables

- ✅ Parser (`cns_py/cql/parser.py`) for MATCH, ASOF, BELIEF, RETURN
- ✅ Executor (`cns_py/cql/executor.py`) with temporal mask, graph traverse, belief compute
- ✅ Planner skeleton (`cns_py/cql/planner.py`)
- ✅ Belief module (`cns_py/cql/belief.py`) with sigmoid + recency
- ✅ Types module (`cns_py/cql/types.py`)
- ✅ ADR 0001 (CQL v0.1 freeze)
- ✅ Unit tests (parser, executor, belief)
- ✅ Golden tests (4 JSON files)

**Status (2025-10-06)**

- ✅ All deliverables complete
- ✅ Tests passing
- ✅ CQL v0.1 frozen and documented

---

## Phase 3 — Contradiction Detection + Docs (Week 3) ✅ COMPLETE

**Objective:** Implement contradiction detection and expand documentation.

### Deliverables

- ✅ `cns_py/cql/contradict.py` — Fiber and atom contradiction detection
- ✅ `tests/test_contradict.py` — Unit tests with fixtures
- ✅ `docs/05-visualization.md` — IB Explorer design spec
- ✅ `docs/06-ib-vs-db.md` — Positioning document
- ✅ `CONTRIBUTING.md` — Contribution guidelines

**Status (2025-10-06)**

- ✅ All deliverables complete (created 2025-10-06)
- 🔄 Integration testing pending
- ⚠️ `CODE_OF_CONDUCT.md` deferred (standard boilerplate, not blocking)

---

## Phase 4 — Rust Core Alpha (Weeks 3–6) 📋 PLANNED

**Objective:** Stand up the next-gen substrate core without breaking the API.

### Deliverables
- **Journal** (append-only Arrow segments).
- **Graph engine v1** (CSR + Roaring masks).
- **Vector engine v1** (IVF-PQ bulk).
- **Planner v1** (ANN → temporal mask → graph expand).

### Status (2026-01-02)
- ⚠️ Deferred in favor of Explorer (Phase 5).

---

## Phase 6: Vector Index & Learning (Started)
- **Status**: Slice 1 Implementation (Belief Propagation)
- **Goal**: Implement deterministic belief update rule and eventually Vector Index.
- **Budget**: P95 < 250ms (Strict)

### History
- **2026-01-02**: Slice 5 (ANN & Embeddings) - Partial.
    - **5A**: Experimental ANN (`HnswVectorIndex`) implemented and benchmarked.
    - **5B**: Embeddings Pipeline (`EmbeddingProvider`) integrated.
    - **5C**: Filters v2 Deferred.
- **2026-01-02**: Slice 4 (Real Index Lifecycle) Implemented.
    - Added `IndexManager` with startup/shutdown hooks.
    - Added Config (`VECTOR_INDEX_ENABLED`, etc.).
    - Wired API to real DB atoms (enriched response).
    - Validated Persistence Proof (Restart Test).
- **2026-01-02**: Slice 3 (Persistence & Filtering) Complete.
    - **3A**: Persistence (`save/load`, npz+json).
    - **3C**: Filtering (Subset Match).
    - **3B**: Skipped (Prioritized Filtering).
    - Validated with `test_vector_persistence.py` & `test_vector_filtering.py`.
- **2026-01-02**: Slice 2 (Vector Index v0) Implemented.
    - Defined `VectorIndex` contract (ABC).
    - Implemented `ExactInMemoryIndex` and `PgVectorIndex`.
    - Added API `/graph/similar`.
    - Verified Determinism & Perf.
- **2026-01-02**: Slice 1 (Belief Logic) Implemented.
    - Defined update rule: `σ(w_e*E + w_r*R + w_t*T - w_c*C)`
    - Validated with unit tests (`tests/test_belief.py`)
    - Perf Smoke: P95 ~73ms (Deterministic)
- **2026-01-05**: Phase 8 Complete (Executable Memory).
    - **Slice 8.1**: Signed Provenance (Crypto + API).
    - **Slice 8.2**: WASM Runtime (Sandbox).
- **2026-01-05**: Phase 7 Complete (Frontend Integration & Gates).
    - **Slice 7.1**: Frontend "Find Similar" UI and API updates.
    - **Slice 7.2**: Rust Gates (`fmt`, `clippy`, `test`) in CI.
- **2026-01-02**: Phase 6 Complete (Vector Index).
- **2026-01-05**: Phase 9 Complete (Learned Routers).
    - **Slice 9.1**: Multi-Space Indexing (Manager refactoring, API update).
    - **Slice 9.2**: Router v0 (Heuristic regex router).
    - **Slice 9.3**: Benchmarks (Proven 100% recall maintenance with multi-space, P95 latency reduced).
- **2026-01-06**: Phase 10 Complete (Rule-Orchestrated Retrieval).
    - **Slice 10.1**: Retrieval Planner (Det. heuristic planner).
    - **Slice 10.2**: WASM Rules (WAT placeholders).
    - **Slice 10.3**: Signed Outputs (Findings integrity verification).
    - **Slice 10.X**: Verified full pipeline with `demo_phase10.py`.
- **2026-01-06**: Phase 11 Complete (Productionize Pipeline).
    - **Slice 11.1**: Planner Explainability.
    - **Slice 11.2**: Rule Registry & Manifests.
    - **Slice 11.3**: Index Ops (Status/Rebuild).
    - **Slice 11.4**: UI Hardening (Smart Query Panel).
    - **Slice 11.X**: Verified with `demo_phase11.py`.

## Phase 12 — Belief Revision (Weeks 20-22)
**Objective**: Implement time-aware, contradiction-sensitive belief updates with explanations.

### Deliverables
- **Slice 12.1: Belief Revision Engine v1**
    - Time decay (exponential).
    - Contradiction penalty.
    - Component-based calculation.
- **Slice 12.2: Belief Explanations**
    - `POST /belief/explain`.
    - Trace logic for why a belief score exists.
- **Slice 12.3: API/UX Exposure**
    - Add `?explain=true` to graph queries.
    - Optional UI panel.

### Metrics
- Update time < 10ms.
- Deterministic updates (100% stable).


## Phase 7 — Frontend Integration (Slice 7.1) ✅ COMPLETE

**Objective:** Expose vector capabilities to users.

### Status (2026-01-05)
- ✅ "Find Similar" UI shipped.
- ✅ Rust CI gates active.

---

## Phase 8 — Executable Memory & Provenance (Weeks 12–15) ✅ COMPLETE

**Objective:** Make the memory executable and auditable (Smart Graph).

### Deliverables

- **Slice 8.1: Signed Provenance**
  - Content hashes; Ed25519 signatures on Claims; verification endpoint.
- **Slice 8.2: WASM Sandbox**
  - Register rules (WASM binaries); execute on demand.
  
### Status (2026-01-05)
- ✅ Slice 8.1: `cns_py.crypto` & `/provenance/verify` shipped.
- ✅ Slice 8.2: `wasmtime` integrated for WASI modules.

### Metrics

- Rule eval overhead < 30 ms.
- Provenance verify throughput ≥ 10k/s.

**Exit criteria**

- Demo: run a TLS compliance rule → returns NonCompliant claim with signed provenance chain.

---

## Phase 9 — Learned Routers & Multi-Space (Weeks 16-19)

**Objective:** Improve shortlist quality using domain-specific embedding spaces.

### Deliverables
- **Slice 9.1: Multi-Space Indexing**
  - Support `space_name -> index` map.
  - API support for `space` parameter.
- **Slice 9.2: Router v0**
  - Heuristic router: `route(query) -> [(space, weight)]`.
  - `space="auto"` support.
- **Slice 9.3: Benchmarks**
  - Measure Recall@k improvement over single space.

### Metrics
- Recall@k +10-15% vs single-space baseline.

---

## Phase 10 — Rule-Orchestrated Retrieval (Slices 10.1-10.X)

**Objective**: Move from "router picks space" to "planner returns executable plan".

### Deliverables
- **Slice 10.1: Retrieval Planner v0**: Det. planner + executor (Exact/Vector steps).
- **Slice 10.2: WASM Rule Packs v0**: Sandbox rules (TLS, contradictions) with strict IO.
- **Slice 10.3: Signed Outputs v0**: Sign findings/results for provenance.
- **Slice 10.X: End-to-End Demo**: Full pipeline demo.

### Metrics
- Deterministic plan generation (100% stability).
- Rule execution overhead < 50ms.
- Signed verification throughput > 1000/s.

---

## Phase 9 — Learned Routers & Multi-Space (Weeks 15–18)

**Objective:** Increase shortlist quality with domain-specific embedding spaces.

### Deliverables

- Multi-space vector indexing.
- **Router**: classify query → pick space(s).

### Metrics

- Recall@k improves ≥ 10–15% vs single space.

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
- Visualization: saved layouts; provenance color filters; “why/why-not” overlays.

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

---

## Appendix: Phase 0A Receipts (Summary)

- Coverage gate ≥ 75% (temporary; restore to 85% after tests added)

  - Command: `pytest --cov=cns_py --cov-report=xml --cov-report=html --cov-fail-under=75`
  - Artifacts: `coverage-reports-*/coverage.xml`, `coverage-reports-*/htmlcov/`
  - Note: Threshold lowered on 2025-11-13 to unblock CI; plan to add tests for executor provenance, nn search, DB isolation and raise back to 85%.

- pgTAP schema tests

  - Command: `psql "postgres://cns:cns@127.0.0.1:5433/cns" -f tests_pg/pg_tap_smoke.sql`
  - Artifact: `pgtap-results-*/pg_tap_results.tap`

- Performance smoke (P95 ≤ 250ms; P99 ≤ 900ms)

  - Command: `python scripts/perf_smoke.py --iters 300 --warmup 50 --p95-budget-ms 250 --p99-budget-ms 900`
  - Example output:
    ```
    [CI: perf-smoke]
    dataset=seed/demo@HEAD samples=300 warmup=50
    query=resolve_entities p50=XXms p95=XXms p99=XXms
    env=2CPU/4GB; postgres=16; shared_buffers=512MB; work_mem=64MB
    raw=artifacts/perf_smoke.json
    ```

- Property tests (Hypothesis)

  - Command: `pytest --hypothesis-show-statistics --hypothesis-seed=123456`

- Contradictions integration

  - Test: `tests/test_contradiction_integration.py` (generates EXPLAIN on failure)

- SBOM & housekeeping

  - Command: `cyclonedx-py -o sbom-cyclonedx.json`

- CI Run URL: [Pending]
