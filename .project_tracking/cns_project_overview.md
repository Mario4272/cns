# CNS Project Tracking

## 🧭 Vision
CNS = **Cognition-Native Store**.  
Not a database. A **substrate for intelligence**.  
Where DBs store data, CNS stores **intelligence**: atoms (facts, entities, rules) and fibers (relations) with aspects (vector, symbolic, provenance, belief, temporal).

**Goal:** create the first open-source intelligence substrate — bridging storage, reasoning, and learning. Long-term: shift from **DB (Database)** to **IB (Intelligence Base).**

---

## 📂 Repo Bootstrap (done via `bootstrap_cns_repo.sh`)
Repo layout created:

```
cns/
├─ README.md
├─ LICENSE
├─ CONTRIBUTING.md
├─ CODE_OF_CONDUCT.md
├─ Makefile
├─ requirements.txt
├─ docs/            # vision, architecture, roadmap
├─ docker/          # Postgres+pgvector
├─ cns_py/          # Python reference impl
└─ rust_cns/        # Rust skeleton
```

**Quick start:**
```bash
make up
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python cns_py/storage/db.py --init
python cns_py/demo/ingest.py
python cns_py/demo/query.py
```

**Demo output:**  
Shows `FrameworkX` → TLS1.2 before 2025, TLS1.3 after 2025.

---

## 🏗 Architecture

### Substrate of Today (limitations)
- Rows/JSON/vectors bolted on top of Postgres.
- Snapshots instead of temporal truth.
- No native belief, contradiction, or provenance.
- Retrieval-only, not intelligence storage.

### Next-Gen Substrate (CNS)
- **Atoms**: entities, events, rules, programs.
- **Fibers**: typed relations.
- **Aspects**: vector, symbolic, provenance, belief.
- **Tape**: bitemporal time (valid_from, valid_to, observed_at).
- **Planner**: ANN shortlist → temporal mask → graph expand → symbolic verify → belief rank.
- **Learning inside store**: entity resolution, contradiction detection, belief updating.
- **Executable memory**: rules/programs live inside the substrate.

### Tech Stack
- **Rust**: core engine (journal, graph, vector, symbolic, planner).
- **Python**: SDK, ML learners, demos.
- **Wire**: gRPC (control) + Arrow Flight (data plane).
- **Plugins**: WASM for in-store programs.

---

## 🚀 Implementation Roadmap

### Phase 0 — Repo Bootstrap ✅
- Repo scaffolded with Python reference + Rust skeleton.

### Phase 1 — Python Reference (on Postgres)
- Schema: atoms, fibers, aspects, belief, vectors.
- API: `upsert_atom`, `link`, `nn_search`, `as_of`, `traverse_from`.
- Demo: TLS1.2 → TLS1.3 supersession.

### Phase 2 — CQL Draft
- Parser for minimal syntax (`MATCH`, `SIMILAR`, `BELIEF`, `ASOF`).
- Planner skeleton: ANN shortlist + graph traverse.

### Phase 3 — Rust Core Alpha
- Journal (append-only Arrow segments).
- Graph engine (CSR + Roaring bitmaps).
- Vector engine (IVF-PQ + HNSW hot set).
- Symbolic engine (WASM sandbox).
- Planner v1 (ANN→mask→graph).

### Phase 4 — Belief + Learning
- Belief updater (logistic function).
- Contradiction detection (simple subject/predicate clash).
- Entity resolution (prototype).

### Phase 5 — Visualization (IB Explorer)
- WebGL/Three.js frontend:
  - Atoms as stars, fibers as glowing edges.
  - Zoom out = constellations (clusters).
  - Zoom in = aspects view.
  - Time slider = see belief/validity evolve.
  - Contradictions spark visually.
- Goal: “Google Earth for intelligence.”

### Phase 6 — Beyond DB → IB
- Transform CNS into the canonical “IB”:  
  - Multi-dimensional navigation.  
  - Cognitive cartography.  
  - XR integration: walk through your IB.  

---

## 🎨 Visualization Goals
- **Atoms = stars** (color-coded by type: Entity, Concept, Rule).
- **Fibers = glowing edges** (pulse with belief/confidence).
- **Time slider**: fade/appear by valid_from/valid_to.
- **Contradiction arcs**: lightning effects between conflicting atoms.
- **Provenance mode**: filter or colorize by source.
- **XR future**: immersive exploration of IB galaxies.

---

## 📋 Next JR Tasks
1. Validate Python demo runs end-to-end (`make up` → ingest → query).  
2. Flesh out `cns_py/cql/planner.py` to handle simple queries.  
3. Write unit tests for `belief.py` and `contradict.py`.  
4. Expand docs:  
   - Add `docs/05-visualization.md` (galaxy map concept).  
   - Add `docs/06-ib-vs-db.md` (positioning).  
5. Create GitHub Issues for Phase 1–3 deliverables.  
6. (Optional) Start scaffolding visualization frontend with **Three.js** + mock API.

---

⚡ **Guiding mantra for JR:**  
> “Don’t think rows. Don’t think JSON. Don’t think search.  
> Think **intelligence as substrate**. Everything else follows.”

