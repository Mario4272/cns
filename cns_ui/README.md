# CNS Explorer (Tauri)

This is a small desktop Explorer UI for CNS, built with **Tauri + vanilla TypeScript**.

It connects to the FastAPI demo backend and visualizes graph neighborhoods returned by
`GET /graph/neighborhood`, including **ASOF** time filtering.

---

## Prereqs

- Rust toolchain (via `rustup`)
- Node.js + npm
- CNS repo dev DB seeded (see root `README.md` for `make up` / `make run-api`)

---

## Running the Explorer

From the repo root, in one terminal:

```bash
make run-api  # starts FastAPI demo API on http://127.0.0.1:8000
```

In another terminal:

```bash
cd cns_ui
npm install          # first time only
npm run tauri dev
```

This will open the **CNS Explorer** window.

---

## What you can do

- Enter a **label** (e.g. `FrameworkX`), **hops**, **limit**, and optional **ASOF** timestamp.
- Click **Load** to fetch a neighborhood and render it with Three.js:
  - Nodes as spheres, center node highlighted via `center_node_id`.
  - Edges as lines, collapsed into edge-groups for readability.
- Use the **Predicate** filter and **Debug mode** (Raw/Unique) to inspect:
  - Node list (`id: label`).
  - Edge list (e.g. `FrameworkX --supports_tls--> TLS1.2 (x67)`).

With the demo data seeded, you can see the **TLS1.2 → TLS1.3** ASOF cutover for
`FrameworkX` by loading with timestamps before and after `2025-01-01T00:00:00Z`.
