#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="${1:-cns}"
ROOT="$PWD/$REPO_NAME"

mkdir -p "$ROOT"
cd "$ROOT"

echo "==> Creating repo at $ROOT"

# Helper to write files safely
write() {
  local path="$1"; shift
  mkdir -p "$(dirname "$path")"
  cat > "$path" <<'EOF'
'"$@"'
EOF
}

# --- Top-level files ---
cat > .gitignore <<'EOF'
# Python
.venv/
__pycache__/
*.pyc

# Rust/Build
target/

# Editors
.vscode/
.idea/

# OS
.DS_Store

# Docker
cns_pg/
EOF

cat > LICENSE <<'EOF'
MIT License

Copyright (c) 2025 ...

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to do so, subject to the following conditions:
[...trimmed for brevity; paste your preferred MIT text...]
EOF

cat > README.md <<'EOF'
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
