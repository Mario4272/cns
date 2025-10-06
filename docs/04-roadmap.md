# CNS Roadmap

**Goal:** Ship a cognition-native substrate that proves value over "just a DB" in 90 days, then harden.

**Owner:** JR (+ Val/Mario as backseat drivers)

---

## Timeline Overview

| Phase | Duration | Status | Objective |
|-------|----------|--------|-----------|
| **Phase 0** | Week 0 | ✅ Complete | Repo bootstrap + runnable demo |
| **Phase 0A** | Week 0 | ✅ Complete | QA rig (tests, CI, pre-commit) |
| **Phase 1** | Weeks 1-2 | ✅ Complete | Python reference implementation |
| **Phase 2** | Weeks 2-3 | ✅ Complete | CQL draft (parser + executor) |
| **Phase 3** | Week 3 | ✅ Complete | Contradiction detection + docs |
| **Phase 4** | Weeks 3-6 | 📋 Planned | Rust Core Alpha |
| **Phase 5** | Weeks 7-9 | 📋 Planned | IB Explorer (visualization) |
| **Phase 6** | Weeks 9-12 | 📋 Planned | Belief + Learning |
| **Phase 7** | Weeks 12-15 | 📋 Planned | Executable Memory + Signed Provenance |
| **Phase 8** | Weeks 15-18 | 📋 Planned | Learned Routers + Multi-Space |

---

## Phase 0 — Bootstrap ✅ COMPLETE

**Objective:** Repo + runnable demo to align contributors.

### Deliverables
- ✅ Repo scaffold with Python + Postgres + pgvector
- ✅ Docker compose setup
- ✅ Makefile with basic targets
- ✅ Demo: TLS 1.2 → TLS 1.3 supersession with `ASOF` queries

### Exit Criteria
- ✅ `make up` → `ingest.py` → `query.py` produces expected outputs
- ✅ Demo shows temporal reasoning working

### Status (2025-10-06)
- ✅ All deliverables complete
- ⚠️ Rust skeleton deferred to Phase 4

---

## Phase 0A — QA Rig ✅ COMPLETE

**Objective:** Testing and quality infrastructure.

### Deliverables
- ✅ `pyproject.toml` with pytest, hypothesis, testcontainers, coverage
- ✅ CI workflow (`.github/workflows/ci.yaml`) with lint, type, unit, integ, pgTAP, perf
- ✅ Pre-commit hooks (ruff, black, mypy, detect-secrets)
- ✅ Devcontainer for pgvector dev environment

### Exit Criteria
- ✅ CI green on every commit
- ✅ Coverage ≥ 85% (enforced)
- ✅ Pre-commit hooks auto-run

### Status (2025-10-06)
- ✅ All deliverables complete
- ✅ CI pipeline fully operational

---

## Phase 1 — Python Reference ✅ COMPLETE

**Objective:** Prove core concepts with Python + Postgres.

### Deliverables
- ✅ Schema: atoms, fibers, aspects (belief, vectors, temporal)
- ✅ Core API: `upsert_atom`, `link_with_validity`
- ✅ Demo: TLS supersession with temporal queries
- ✅ Basic `ASOF` queries working

### Exit Criteria
- ✅ Demo runs end-to-end
- ✅ Temporal queries return correct results
- ✅ Belief scores computed correctly

### Status (2025-10-06)
- ✅ All deliverables complete
- ⚠️ Full API layer (`nn_search`, `traverse_from`) deferred to Phase 4

---

## Phase 2 — CQL Draft ✅ COMPLETE

**Objective:** Minimal CQL parser + executor.

### Deliverables
- ✅ Parser (`cns_py/cql/parser.py`) for MATCH, ASOF, BELIEF, RETURN
- ✅ Executor (`cns_py/cql/executor.py`) with temporal mask, graph traverse, belief compute
- ✅ Planner skeleton (`cns_py/cql/planner.py`)
- ✅ Belief module (`cns_py/cql/belief.py`) with sigmoid + recency
- ✅ Types module (`cns_py/cql/types.py`)
- ✅ ADR 0001 (CQL v0.1 freeze)
- ✅ Unit tests + golden tests

### Exit Criteria
- ✅ CQL queries parse correctly
- ✅ Executor returns results with confidence + provenance
- ✅ Golden tests pass

### Status (2025-10-06)
- ✅ All deliverables complete
- ✅ CQL v0.1 frozen and documented

---

## Phase 3 — Contradiction Detection + Docs ✅ COMPLETE

**Objective:** Implement contradiction detection and expand documentation.

### Deliverables
- ✅ `cns_py/cql/contradict.py` — Fiber and atom contradiction detection
- ✅ `tests/test_contradict.py` — Unit tests with fixtures
- ✅ `docs/05-visualization.md` — IB Explorer design spec
- ✅ `docs/06-ib-vs-db.md` — Positioning document
- ✅ `CONTRIBUTING.md` — Contribution guidelines
- ✅ `CODE_OF_CONDUCT.md` — Standard Contributor Covenant
- ✅ `docs/01-vision.md` — Vision and philosophy
- ✅ `docs/02-architecture.md` — Technical architecture
- ✅ `docs/03-cql-spec.md` — CQL language specification
- ✅ `docs/04-roadmap.md` — This document

### Exit Criteria
- ✅ Contradiction detection finds known conflicts
- ✅ Documentation complete and organized

### Status (2025-10-06)
- ✅ All deliverables complete
- 🔄 Integration testing pending

---

## Phase 4 — Rust Core Alpha 📋 PLANNED

**Objective:** Stand up Rust engine with basic journal, graph, and vector operations.

**Timeline:** Weeks 3-6

### Deliverables
- [ ] **Journal v0**: Append-only Arrow segments with bitemporal headers
- [ ] **Graph engine v0**: CSR (Compressed Sparse Row) + Roaring bitmaps for 1-2 hop traversals
- [ ] **Vector engine v0**: IVF-PQ for bulk + HNSW for hot set (100M vectors target)
- [ ] **Planner v0**: ANN shortlist → temporal mask → graph expand pipeline
- [ ] **Wire protocol**: Arrow Flight for result sets, gRPC for control ops
- [ ] **Python SDK**: Feature flag to swap Postgres backend for Rust backend

### Metrics
- P95 ≤ 150ms on: ANN shortlist (1M vectors) → 2-hop traverse → belief filter
- Journal replay produces identical results to live execution

### Exit Criteria
- [ ] Rust engine passes same golden tests as Python reference
- [ ] Python demo works with `--engine=rust` flag
- [ ] Results match Python within tolerance

### Risks
- **Complexity**: Rust engine is 10x more complex than Python
- **Integration**: Arrow Flight + gRPC adds moving parts
- **Performance**: IVF-PQ + HNSW tuning is non-trivial

### Mitigation
- Start with minimal viable implementations
- Use property-based tests to catch semantic mismatches
- Benchmark early and often
- Keep Python reference as source of truth

---

## Phase 5 — IB Explorer Alpha 📋 PLANNED

**Objective:** Ship the galaxy map visualization to make CNS tangible.

**Timeline:** Weeks 7-9

### Deliverables
- [ ] **WebGL/Three.js frontend**: Atoms as stars, fibers as edges
- [ ] **Time slider**: Scrub through temporal dimension
- [ ] **Contradiction mode**: Lightning arcs between conflicts
- [ ] **Detail panels**: Click atom → see aspects, provenance, belief history
- [ ] **Zoom levels**: Clusters → subgraphs → atom detail

### Metrics
- 60 FPS on 10k atoms + 50k fibers on laptop GPU
- < 100ms detail panel load on atom click
- < 500ms time slider scrub response
- < 1s CQL query → visualization update

### Exit Criteria
- [ ] Live demo: switch dates; see TLS claim swap + contradiction animation
- [ ] Click atom to view sources and belief history
- [ ] Smooth performance on target hardware

### Prerequisites
- Phase 4 Rust engine (for fast queries to power UI)
- `docs/05-visualization.md` (✅ done) as design spec
- Demo data with contradictions

---

## Phase 6 — Belief + Learning 📋 PLANNED

**Objective:** Move beyond static data to learning inside the store.

**Timeline:** Weeks 9-12

### Deliverables
- [ ] **Belief updater**: Scheduled job to recompute confidence scores
- [ ] **Contradiction detection**: Automatic surfacing (already have `contradict.py`!)
- [ ] **Entity resolution (prototype)**: Embedding + graph features → `same_as` fibers
- [ ] **Belief math v2**: Add source reputation and contradiction penalties

### Metrics
- Entity resolution: ≥ 90% precision, ≥ 80% recall on test dataset
- Contradiction detection: 100% of known conflicts found
- Belief updates: < 1s per 1000 atoms

### Exit Criteria
- [ ] Scheduled jobs run reliably
- [ ] Entity resolution creates `same_as` fibers with provenance
- [ ] Contradiction detection integrated with belief updates

### Prerequisites
- Phase 4 Rust engine (for performance at scale)
- Contradiction detection tested (✅ done)
- Belief math validated on real data

---

## Phase 7 — Executable Memory + Signed Provenance 📋 PLANNED

**Objective:** Make the memory executable and auditable.

**Timeline:** Weeks 12-15

### Deliverables
- [ ] **WASM Sandbox**: Register rules/resolvers/summarizers; execute on demand
- [ ] **Signed provenance (optional mode)**: Ed25519 signatures on source + derived claims
- [ ] **Verification endpoint**: Check signatures and content hashes
- [ ] **Provenance chains**: Trace derived claims back to originals

### Metrics
- Rule eval overhead < 30ms per invocation for small payloads
- Provenance verify throughput ≥ 10k/s on single core

### Exit Criteria
- [ ] Demo: run TLS compliance rule → returns NonCompliant claim with signed provenance chain
- [ ] Signature verification working end-to-end

---

## Phase 8 — Learned Routers + Multi-Space 📋 PLANNED

**Objective:** Increase shortlist quality with domain-specific embedding spaces.

**Timeline:** Weeks 15-18

### Deliverables
- [ ] Multi-space vector indexing (e.g., `sec_proto`, `legal_v1`, `code_v1`)
- [ ] **Router**: Classify query → pick space(s) + weights
- [ ] Small adapter training loop

### Metrics
- Recall@k improves ≥ 10-15% vs single space on mixed-domain benchmark

### Exit Criteria
- [ ] CQL `SIMILAR(x, "text", space="auto")` outperforms fixed space on demo corpus

---

## Always-On Operations (Phases 1-∞)

### Metrics & Tracing
- OTel spans per operator
- Prometheus counters (ANN, traverse, rule, belief)

### Backups
- Journal snapshots → object store
- One-command restore

### Security
- Capability-based ACLs per atom/fiber/aspect
- License tags enforced in learners

### CI
- Unit + golden tests + perf smoke
- ANN P95, traverse P95 gates

---

## Demos to Ship (Sales/README-ready)

### 1. Truth-as-of
**Question:** "What did Framework X require on 2024-12-31 vs 2025-09-30?"

**Output:**
- Different TLS versions
- `SUPERCEDES` link
- Citations
- `EXPLAIN` mode

### 2. Contradiction Surfacing
**Scenario:** Two papers disagree on a claim

**Output:**
- Lightning edge between conflicting atoms
- Belief shift visualization
- Source citations for both sides

### 3. IB Explorer
**Features:**
- Galaxy view (atoms as stars)
- Time slider
- Click to see provenance
- Contradiction mode

### 4. Executable Memory
**Scenario:** Run a TLS compliance rule

**Output:**
- NonCompliant claim
- Signed provenance chain
- Rule execution trace

---

## Acceptance Gate (Go/No-Go to Beta)

Before declaring "Beta" status, we must have:

- [ ] CQL v0.1 stable; tests passing
- [ ] P95 ≤ 150ms on Rust engine alpha targets
- [ ] 100% answers with citations; `EXPLAIN` readable
- [ ] IB Explorer demo smooth at 10k nodes
- [ ] Journal snapshot/replay proven identical
- [ ] At least 2 of 4 demos shipped and documented

---

## Issue Backlog (Future Work)

### CQL Enhancements
- Edge labels and qualifiers
- LIMIT/ORDER/pagination
- Multi-hop path patterns
- Aggregations (COUNT, SUM, AVG)
- Subqueries

### Planner Improvements
- Better cost model (mask selectivity, fanout estimates)
- Query optimization (push-down filters, join reordering)
- Adaptive query execution

### Belief System
- Domain weights
- Source reputation model
- Contradiction penalties
- User-defined belief functions

### Entity Resolution
- Embedding-based features
- Graph-based features
- Active learning loop
- Quarantine for uncertain merges

### Vector Engine
- Bundles: parameterize size/coverage
- Auto-demotion heuristics
- Multi-space indexing
- Learned routing

### Wire Protocol
- Arrow Flight integration
- Columnar result frames
- Zero-copy to frontend
- Streaming results

### Security
- Signed provenance toggle
- Export scrubber (license-aware)
- Row-level security
- Audit logging

### Visualization
- Saved layouts
- Provenance color filters
- "Why/why-not" overlays
- XR mode (VR/AR)

---

## Success Metrics (90 Days)

### Technical
- [ ] Rust engine passes 100% of Python golden tests
- [ ] P95 query latency ≤ 150ms on 1M atom + 5M fiber dataset
- [ ] Contradiction detection finds 100% of known conflicts
- [ ] IB Explorer renders 10k atoms at 60 FPS

### Process
- [ ] CI green on every commit
- [ ] Test coverage ≥ 85% (enforced)
- [ ] All PRs reviewed within 24 hours
- [ ] Documentation updated in same PR as code

### Community (if open-sourcing)
- [ ] 10+ GitHub stars
- [ ] 3+ external contributors
- [ ] 5+ issues/discussions from non-team
- [ ] 1+ blog post or demo video

---

## Long-Term Vision (Beyond 90 Days)

### Year 1
- Production-ready Rust engine
- 100M+ atoms, 1B+ fibers
- Multi-tenant deployment
- Commercial pilot customers

### Year 2
- XR visualization (VR/AR)
- Multi-space vector indexing
- Federated intelligence bases
- Industry standard for IB

### Year 3+
- Shift from "DB" to "IB" terminology
- CNS as canonical IB reference implementation
- Ecosystem of learners, visualizations, tools
- "Google Earth for knowledge graphs"

---

## References

- `.project_tracking/cns_project_overview.md` — Original project tracking
- `.project_tracking/cns_phased_build_plan.md` — Detailed phase breakdown
- `.project_tracking/remediation_and_next_phase_plan.md` — Status audit + next steps
- `docs/01-vision.md` — Vision and philosophy
- `docs/02-architecture.md` — Technical architecture
- `docs/03-cql-spec.md` — CQL specification
- `docs/05-visualization.md` — IB Explorer design
- `docs/06-ib-vs-db.md` — IB vs DB comparison

---

**Last Updated:** 2025-10-06  
**Status:** Phases 0-3 complete, Phase 4 next
