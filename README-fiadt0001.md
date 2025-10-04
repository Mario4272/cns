# CNS — Cognition-Native Store
**Not a database. A substrate for intelligence.**

CNS stores and reasons over **Atoms** (facts, entities, rules, programs) and **Fibers** (typed relations) with co-resident **Aspects**:
- `vector[]` (multi-space semantics), `symbol` (AST/Datalog/SMT), `text`, `media`
- `belief` (confidence/evidence/contradictions/recency)
- `provenance` (signed source chains)
- `tape` (bitemporal: `valid_from`, `valid_to`, `observed_at`)

It runs learning **inside** the store (entity resolution, contradiction detection, summarization, belief update) and supports **CQL**, a cognition query language blending similarity, structure, time, and executable rules.

## Quick start

### 1) Start Postgres with pgvector
```bash
make up
