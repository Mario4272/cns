# CNS Explorer — Manual Smoke Recipe

This is a short, exact manual recipe to verify the CNS Explorer in Demo Mode.

## 1. Start the FastAPI demo API (@ http://127.0.0.1:8000)

From the repo root:

```bash
make run-api
```

## 2. Start the Explorer UI (Tauri via npm)

From the repo root:

```bash
cd cns_ui
npm install       # first time only
npm run tauri dev
```

## 3. Smoke steps

In the Explorer window:

1. Load **FrameworkX** neighborhood

   - Label: `FrameworkX`
   - Hops: `1`
   - Limit: `100`
   - Predicate: `supports_tls`
   - Click **Load**

2. Toggle ASOF before/after TLS cutover and inspect detail

   - Choose an ASOF **before** TLS1.3 (e.g. `2024-12-31T23:59:59Z`)
   - Click **Load**
   - Click a node and confirm `/graph/node/{id}?asof=…` reflects TLS1.2.
   - Then set ASOF **after** TLS1.3 (e.g. `2025-01-01T00:00:01Z`) and repeat.

3. Hover node/edge → hover strip updates

   - Move the mouse over nodes and edges.
   - Confirm the hover strip text updates with node/edge identity.

4. Reset camera works

   - Pan/zoom the scene.
   - Click **Reset camera** and confirm the view snaps back to the initial framing.

5. Copy debug bundle
   - With a neighborhood loaded, click **Copy debug bundle**.
   - Paste into a text editor or GitHub comment.
   - Confirm the JSON contains `query`, `response_meta`, and sampled `nodes`/`edges`.

## 4. Optional CLI smoke (ASOF, contradictions, policy)

From the repo root with `make run-api` running, you can also verify the core
engine behavior via `curl`.

### 4.1 ASOF cutover (FrameworkX)

```bash
# Before TLS1.3 cutover: expect supports_tls -> TLS1.2
curl "http://127.0.0.1:8000/graph/node/$(
  curl -s "http://127.0.0.1:8000/graph/neighborhood?label=FrameworkX&hops=1" \
    | jq '.nodes[] | select(.label=="FrameworkX") | .id'
)" \
  "?asof=2024-12-31T23:59:59Z" | jq '.aspects[] | select(.predicate=="supports_tls")'

# After cutover: expect supports_tls -> TLS1.3
curl "http://127.0.0.1:8000/graph/node/$(
  curl -s "http://127.0.0.1:8000/graph/neighborhood?label=FrameworkX&hops=1" \
    | jq '.nodes[] | select(.label=="FrameworkX") | .id'
)" \
  "?asof=2025-01-01T00:00:01Z" | jq '.aspects[] | select(.predicate=="supports_tls")'
```

### 4.2 Contradictions (FrameworkY)

```bash
# Pick any supports_tls edge for FrameworkY and inspect contradictions
curl "http://127.0.0.1:8000/graph/neighborhood?label=FrameworkY&hops=1&asof=2025-06-01T00:00:00Z" \
  | jq '.edges[] | select(.predicate=="supports_tls") | .id' | head -n1 | {
      read eid
      curl "http://127.0.0.1:8000/graph/edge/$eid?asof=2025-06-01T00:00:00Z"
    }
```

You should see a non-empty `contradictions[]` array on the edge detail, and the
contradicting edge will list the original in its own `contradictions[]`.

### 4.3 Truth policy (FrameworkY)

```bash
# Neighborhood with all competing claims (FrameworkY supports TLS1.2 AND TLS1.3)
curl "http://127.0.0.1:8000/graph/neighborhood?label=FrameworkY&hops=1&asof=2025-06-01T00:00:00Z&policy=all" \
  | jq '.edges[] | select(.predicate=="supports_tls")'

# Neighborhood with only one winner per (src,predicate) group
curl "http://127.0.0.1:8000/graph/neighborhood?label=FrameworkY&hops=1&asof=2025-06-01T00:00:00Z&policy=latest" \
  | jq '.edges[] | select(.predicate=="supports_tls")'
```

In the second call you should see exactly one `supports_tls` edge for FrameworkY
instead of both TLS1.2 and TLS1.3.

## 5. Perf smoke (CQL-level)

You can run a lightweight performance/determinism smoke over the core CQL
queries that back the Explorer.

From the repo root, with the API up (for database access) and your venv
activated:

```bash
python -m scripts.perf_smoke --iters 50 --warmup 10
```

This will:

- Run a pair of CQL queries (FrameworkX `supports_tls` before/after cutover)
  multiple times.
- Compute p50 / p95 / p99 latencies and write a markdown summary to
  `perf_summary.md`.
- Check that the result sets are deterministic for each fixed query.
- Exit non-zero if:
  - Any query returns non-deterministic results, or
  - The worst p95 across queries exceeds the configured budget (default 500ms).

Use this as a quick regression check before heavier changes. If `perf_smoke`
fails, inspect `perf_summary.md` and `perf_last_explain.json` for details.
