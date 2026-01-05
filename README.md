# CNS — Cognition-Native Store

**Not a database. A substrate for intelligence.**

CNS stores and reasons over **Atoms** (facts, entities, rules, programs) and **Fibers** (typed relations) with co-resident **Aspects**:

- `vector[]` — multi-space semantics (pgvector/N dims)
- `symbol` — AST / Datalog / SMT terms
- `text` — canonical and free-form strings
- `media` — blobs + typed metadata
- `belief` — confidence, evidence, contradictions, recency
- `provenance` — signed source chains
- `tape` — bitemporal: `valid_from`, `valid_to`, `observed_at`

Learning happens **inside** the store (resolution, contradiction detection, summarization, belief updates) and is addressable via **CQL**, a cognition query language blending similarity, structure, time, and executable rules.

---

## Repo layout (tl;dr)

```
cns/
├─ cns_py/              # Python core: CQL executor, graph, demo API, helpers
│  ├─ api/              # FastAPI demo server (/cql, /graph/neighborhood)
│  └─ cql/, graph/, ... # planner, traversal, belief math, etc.
├─ migrations/          # SQL migrations (golang-migrate style)
├─ scripts/             # local dev helpers (bash/ps1)
├─ cns_ui/              # Tauri + TS desktop Explorer (IB Explorer Alpha)
├─ Makefile             # see targets below
└─ .env.example         # sample config
```

---

## Quick start

### 0) Prereqs

- Docker + Docker Compose
- `make`
- (Optional) `psql` CLI for local poking

### 1) Bring up Postgres (with pgvector) and CNS

Run these **from the repo root**:

```bash
# 1) Start infra
make up
# waits until Postgres is healthy, pgvector ready, CNS API boots
```

The `make up` target will:

- start `postgres` with `pgvector` installed
- run migrations in `migrations/`
- seed minimal system rows (builtin spaces, root rules)
- start `cns-api` on `http://localhost:8080`

If you prefer it verbose:

```bash
docker compose up -d
./scripts/wait-for-db.sh
./scripts/migrate.sh up
./scripts/seed.sh minimal
```

### 2) Verify

```bash
# Check extension + schema
scripts/psql.sh -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname FROM pg_extension WHERE extname='vector';"
scripts/psql.sh -c "\dt cns.*"
```

### 3) Insert a hello-world Atom (HTTP)

```bash
curl -X POST http://localhost:8080/v1/atom \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "entity",
    "label": "person",
    "text": "Paige Fialho",
    "aspects": {
      "belief": {"p": 0.94, "source": "seed"},
      "tape": {"observed_at": "now"}
    }
  }'
```

### 4) Run a tiny CQL query

```bash
curl -X POST http://localhost:8080/cql -H "Content-Type: application/json" -d '{
  "query": "MATCH label=\"FrameworkX\" PREDICATE supports_tls ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE"
}'
```

Output:

```json
{
  "results": [
    {
      "subject_label": "FrameworkX",
      "predicate": "supports_tls",
      "object_label": "TLS1.3",
      "confidence": 0.958,
      "fiber_id": 495,
      "observed_at": "2026-01-02T17:54:09.078654+00:00",
      "provenance": [
        {
          "source_id": "demo_seed:fiber:495",
          "uri": "https://example.org/demo/tls-policy",
          "line_span": null,
          "fetched_at": "2026-01-02T17:54:09.077461+00:00",
          "hash": "demo-sha256-placeholder"
        }
      ]
    }
  ],
  "explain": {
      "steps": ["... (execution plan) ..."],
      "total_ms": 12.3
  }
}
```

---

## Configuration

Copy the example and adjust:

```bash
cp .env.example .env
# minimally set:
# CNS_DB_URL=postgres://cns:cns@localhost:5432/cns?sslmode=disable  # pragma: allowlist secret
# CNS_API_PORT=8080
# CNS_VECTOR_DIMS=1536
```

---

## Data model (minimum viable)

**Atoms** (`cns.atom`)

- `id uuid pk`
- `kind text` — `entity|fact|rule|program`
- `label text` — type name (e.g., `person`, `company`, `address`)
- `text text` — canonical text form
- `symbol jsonb` — AST/terms (nullable)
- `media bytea` + `media_type text` (nullable)
- `vector vector` — length = `CNS_VECTOR_DIMS` (nullable)
- `created_at timestamptz`
- `updated_at timestamptz`

**Fibers** (`cns.fiber`)

- `src uuid fk → atom.id`
- `dst uuid fk → atom.id`
- `rel text` — relation type (e.g., `knows`, `located_in`)
- `weight real` — soft strength
- `tape_valid tstzrange` — bitemporal validity
- `observed_at timestamptz`
- `provenance jsonb` — signed chain
- `belief jsonb` — `{p, evidence[], contradictions[]}`

**Indices**

- GIN on `symbol`, `provenance`
- HNSW/ivfflat on `vector`
- B-tree on `label`, `(src,rel,dst)`, `observed_at`

---

## Belief & Tape (bitemporal)

- `belief.p` in `[0,1]`; Bayesian update with source reliability
- `contradictions[]` carry pointers to conflicting atoms/fibers
- `tape_valid` uses `tstzrange(valid_from, valid_to)`
- `observed_at` anchors when we first saw it (ingest clock)

---

## Learning jobs (in-store)

- **Resolution**: semantic + symbolic + graph features → merge/same-as fibers
- **Contradiction detection**: rule-backed diffs over overlapping `tape_valid`
- **Summarization**: compress neighborhood → `summary` atoms with provenance
- **Belief update**: scheduled recalculation after new evidence

Run locally:

```bash
make jobs    # runs all jobs once
make jobs/er # just entity resolution
```

---

## CQL (Cognition Query Language) — tiny preview

Similarity + structure:

```sql
MATCH (p:person)-[r:knows]->(q:person)
WHERE sim(p.vector, :$emb("Alex from Jensen-verse")) > 0.75
AND   tape_overlaps(r.tape_valid, '2020-01-01', '2024-12-31')
RETURN p, q, r
ORDER BY belief(r).p DESC
LIMIT 25;
```

Executable rule:

```sql
RULE likely_duplicate(p, q) :-
  label(p)='person' AND label(q)='person'
  AND sim(p.vector, q.vector) > 0.92
  AND overlap(name(p), name(q)) > 0.8;
```

Time-aware contradiction:

```sql
SELECT contradicting_pairs(a1, a2)
FROM atoms a1, atoms a2
WHERE a1.label='address' AND a2.label='address'
AND entity_of(a1)=entity_of(a2)
AND a1.text != a2.text
AND tape_overlap(a1, a2);
```

---

## Make targets (run from repo root)

```bash
make up            # compose up + migrate + seed + core API (legacy)
make down          # stop containers
make logs          # tail api + db logs
make migrate/up    # apply migrations
make migrate/down  # rollback last migration
make seed          # load minimal builtin spaces + rules
make dev           # hot-reload api (watchexec/nodemon/go-run etc.)
make jobs          # run all learning jobs once
make run-api       # run FastAPI demo API (CQL + /graph/neighborhood) locally
```

---

## Local development notes

- **Where to run things**

  - All `make` commands: **repo root**
  - SQL pokes: `scripts/psql.sh -c "..."` (wraps `psql` with env)
  - FastAPI demo API: `make run-api` (serves `/cql` and `/graph/neighborhood` on `http://127.0.0.1:8000`)
  - Desktop Explorer: see `cns_ui/README.md` for the Tauri-based IB Explorer UI

- **Vector dims** must match your embedder. Default `1536` (OpenAI-like). Change `CNS_VECTOR_DIMS` and re-migrate if you switch.
- **Idempotency**: seeds and jobs are idempotent; safe to rerun.
- **Zero-trust provenance**: signers/keys recorded in `provenance`; verification runs on ingest and prior to merges.

---

## Security (dev default)

- Dev brings up Postgres without TLS and API with no auth. Please don’t point it at the internet (hi, future you).
- Prod profile: mTLS between API and DB, signed provenance enforcement, audit log on all rule executions, row-level security on tenants.

---

## Roadmap (short)

- [ ] CQL planner heuristics v1 (vector + symbolic co-planning)
- [ ] Online ER (streaming merges with quarantine)
- [ ] Belief math plugin API
- [ ] Snapshot/restore of bitemporal slices
- [ ] Multi-embedder spaces per aspect

---

## Status

Pre-alpha. Expect breaking changes. If it breaks, you own both halves (kidding… mostly).

---

## Usage instructions

**Coming Soon!!** Once we have something that works, we’ll update that.

## Branching Model

This project follows a strict branching strategy:
- **`dev`**: The active development branch. All feature work, experiments, and PRs target `dev`.
- **`main`**: The stable release branch. We only merge `dev` to `main` after all verification gates (tests, lint, perf) are green.

**Submitting Changes**:
1. Checkout `dev`.
2. Create your feature branch off `dev`.
3. Submit PR to `dev`.
4. After validation, `dev` is promoted to `main`.
