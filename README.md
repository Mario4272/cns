# CNS — Cognition-Native Store

**Not a database. A substrate for intelligence.**

CNS stores and reasons over **Atoms** (facts, entities, rules, programs) and **Fibers** (typed relations) with co-resident **Aspects**:

* `vector[]` — multi-space semantics (pgvector/N dims)
* `symbol` — AST / Datalog / SMT terms
* `text` — canonical and free-form strings
* `media` — blobs + typed metadata
* `belief` — confidence, evidence, contradictions, recency
* `provenance` — signed source chains
* `tape` — bitemporal: `valid_from`, `valid_to`, `observed_at`

Learning happens **inside** the store (resolution, contradiction detection, summarization, belief updates) and is addressable via **CQL**, a cognition query language blending similarity, structure, time, and executable rules.

---

## Repo layout (tl;dr)

```
cns/
├─ api/                 # HTTP/gRPC adapters, auth, request → CQL
├─ cql/                 # parser, planner, rule engine, builtin ops
├─ core/                # atoms, fibers, aspects, belief math
├─ store/               # Postgres schema, views, triggers, pgvector ops
├─ jobs/                # ER, contradiction detection, summarization
├─ migrations/          # SQL migrations (golang-migrate style)
├─ scripts/             # local dev helpers (bash/ps1)
├─ Makefile             # see targets below
└─ .env.example         # sample config
```

---

## Quick start

### 0) Prereqs

* Docker + Docker Compose
* `make`
* (Optional) `psql` CLI for local poking

### 1) Bring up Postgres (with pgvector) and CNS

Run these **from the repo root**:

```bash
# 1) Start infra
make up
# waits until Postgres is healthy, pgvector ready, CNS API boots
```

The `make up` target will:

* start `postgres` with `pgvector` installed
* run migrations in `migrations/`
* seed minimal system rows (builtin spaces, root rules)
* start `cns-api` on `http://localhost:8080`

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
curl -X POST http://localhost:8080/v1/cql -H "Content-Type: application/json" -d '{
  "query": "
    MATCH (p:person)
    WHERE text ~ \"Paige\"
    RETURN p, belief(p), tape(p)
    LIMIT 5
  "
}'
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

* `id uuid pk`
* `kind text` — `entity|fact|rule|program`
* `label text` — type name (e.g., `person`, `company`, `address`)
* `text text` — canonical text form
* `symbol jsonb` — AST/terms (nullable)
* `media bytea` + `media_type text` (nullable)
* `vector vector` — length = `CNS_VECTOR_DIMS` (nullable)
* `created_at timestamptz`
* `updated_at timestamptz`

**Fibers** (`cns.fiber`)

* `src uuid fk → atom.id`
* `dst uuid fk → atom.id`
* `rel text` — relation type (e.g., `knows`, `located_in`)
* `weight real` — soft strength
* `tape_valid tstzrange` — bitemporal validity
* `observed_at timestamptz`
* `provenance jsonb` — signed chain
* `belief jsonb` — `{p, evidence[], contradictions[]}`

**Indices**

* GIN on `symbol`, `provenance`
* HNSW/ivfflat on `vector`
* B-tree on `label`, `(src,rel,dst)`, `observed_at`

---

## Belief & Tape (bitemporal)

* `belief.p` in `[0,1]`; Bayesian update with source reliability
* `contradictions[]` carry pointers to conflicting atoms/fibers
* `tape_valid` uses `tstzrange(valid_from, valid_to)`
* `observed_at` anchors when we first saw it (ingest clock)

---

## Learning jobs (in-store)

* **Resolution**: semantic + symbolic + graph features → merge/same-as fibers
* **Contradiction detection**: rule-backed diffs over overlapping `tape_valid`
* **Summarization**: compress neighborhood → `summary` atoms with provenance
* **Belief update**: scheduled recalculation after new evidence

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
make up            # compose up + migrate + seed + api
make down          # stop containers
make logs          # tail api + db logs
make migrate/up    # apply migrations
make migrate/down  # rollback last migration
make seed          # load minimal builtin spaces + rules
make dev           # hot-reload api (watchexec/nodemon/go-run etc.)
make jobs          # run all learning jobs once
```

---

## Local development notes

* **Where to run things**

  * All `make` commands: **repo root**
  * SQL pokes: `scripts/psql.sh -c "..."` (wraps `psql` with env)
* **Vector dims** must match your embedder. Default `1536` (OpenAI-like). Change `CNS_VECTOR_DIMS` and re-migrate if you switch.
* **Idempotency**: seeds and jobs are idempotent; safe to rerun.
* **Zero-trust provenance**: signers/keys recorded in `provenance`; verification runs on ingest and prior to merges.

---

## Security (dev default)

* Dev brings up Postgres without TLS and API with no auth. Please don’t point it at the internet (hi, future you).
* Prod profile: mTLS between API and DB, signed provenance enforcement, audit log on all rule executions, row-level security on tenants.

---

## Roadmap (short)

* [ ] CQL planner heuristics v1 (vector + symbolic co-planning)
* [ ] Online ER (streaming merges with quarantine)
* [ ] Belief math plugin API
* [ ] Snapshot/restore of bitemporal slices
* [ ] Multi-embedder spaces per aspect

---

## Status

Pre-alpha. Expect breaking changes. If it breaks, you own both halves (kidding… mostly).

---

## Usage instructions

**Coming Soon!!** Once we have something that works, we’ll update that.
