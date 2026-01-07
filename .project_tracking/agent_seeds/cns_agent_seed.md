# CNS Agent Guidelines (Code Quality, Performance, Determinism)

These rules apply to all contributors and AI coding agents working on CNS (Cognition-Native Store).
If you touch code, you follow this. No exceptions. No “quick fix” folklore.

## Scope

Applies to:
- Python service code, libraries, CLIs, scripts
- SQL schema/migrations and query logic (CQL and any SQL helpers)
- Rust code (if present now or later), including WASM runtime components
- CI, tooling, docs, and GitHub workflows

## CNS Core Principles

### 1) Determinism is a feature, not a suggestion
- Any query path that claims determinism must be verifiably deterministic in tests.
- Tie-breakers must be explicit and stable (never rely on implicit DB ordering).
- If a “latest” concept exists, define it precisely (timestamp, priority, confidence, and deterministic tie rules).

### 2) Performance is a product requirement
- Keep p95 within defined budgets for “smoke” and “explorer” workloads.
- If you add functionality that affects query paths, you must update or extend perf harness coverage.
- Prefer algorithmic wins and data model improvements over micro-optimizations.

### 3) Correctness beats cleverness
- Clear invariants, explicit errors, and tests that prove behavior.
- No hidden behavior, no spooky action-at-a-distance state.

### 4) Small diffs, strong receipts
- PRs should be scoped and reviewable.
- Every non-trivial change must include: tests, docs update (if applicable), and a short rationale.

## Repo Hygiene is important

- No commented-out code.
- No debug prints committed.
- No hardcoded secrets or credentials.
- Follow the project’s formatting and lint rules. If tooling disagrees with you, tooling wins.
- Log files (e.g name.log, name.txt, etc) go into .logs folder on the root, which is not tracted by git

## Required Tooling

### Git + GitHub
- Use `gh` CLI for issue and PR work.
- Reference issues in PR descriptions.
- Prefer “close with keywords” when appropriate (e.g., “Closes #123”).
- Using Pre-COmmit is an absolute requirement.

### Python
- Use the repo’s pinned tooling (pre-commit, ruff/black/mypy/pytest as configured).
- Do not introduce new global state unless explicitly part of architecture.
- Avoid heavy dependencies unless they materially simplify the system or unlock performance.

### Postgres / SQL
- Assume production workloads.
- Avoid nondeterministic query results: always use explicit ordering where it matters.
- Prefer set-based queries and indexes over app-side loops.

### Rust (if used)
- Use `cargo`, `rustfmt`, `clippy`.
- No `unsafe` without documented invariants and a strong justification.
- No `.unwrap()` in production paths. Use typed errors.

## GitHub Issues Discipline (using gh)

### Always start by syncing reality with Issues
When beginning work, do this:
- List open issues and priorities
- Confirm what you’re solving and what “done” means

Suggested commands:
- `gh issue list --state open --limit 50`
- `gh issue list --label bug --state open`
- `gh issue view <N>`

### Triage rules
- If you discover a bug while working: open an issue immediately with repro steps and expected behavior.
- If you find a missing test case: open an issue or add the test in the same PR, but do not ignore it.

### PR linking rules
- Every PR must reference an issue (existing or newly created), unless it’s a trivial doc typo.
- PR description must include:
  - What changed
  - Why it changed
  - How it was tested
  - Any perf/determinism impact

## Error Handling Standards

### Python
- Use explicit exception types or structured error results where appropriate.
- Add context at boundaries (IO, DB calls, external interfaces).
- Do not swallow exceptions without logging and a reason.

### SQL
- Prefer constraints to enforce invariants.
- Use transactions for multi-step changes.
- Make migrations reversible when feasible.

### Rust
- Use `thiserror` for library error types.
- Use `anyhow` only at application boundaries (CLI / main / service entrypoints).
- Avoid panics; use `expect()` only for invariant violations with a specific message.

## Determinism Requirements (CNS-Specific)

These are mandatory for query and scoring logic:
- If two results are “equal” by ranking criteria, ties must break deterministically:
  - stable secondary keys (e.g., timestamp, then id)
- “Latest” must be defined:
  - by a specific timestamp field (or explicit precedence rules)
- Contradictions must have a defined behavior:
  - whether both persist, whether one masks another, and how retrieval resolves it

Any change to these rules requires:
- Updated tests covering edge cases
- Updated docs describing the behavior

## Performance Requirements (CNS-Specific)

- If a change touches query execution, traversal, indexing, or scoring:
  - run perf harness locally
  - ensure p95 stays within budget (or explicitly justify regression with numbers)
- Prefer:
  - better indexes
  - reduced query count
  - less data transfer
  - fewer allocations and conversions in hot paths

## Testing Requirements

### General
- New behavior requires tests.
- Bug fixes require regression tests.
- Tests must be deterministic: no time-dependent randomness without fixed seeds.

### Python tests
- Use pytest.
- Avoid flakey integration setup; prefer isolated ephemeral DBs / templates as configured.
- Mock external services and file systems unless the test is explicitly an integration test.

### SQL
- Any schema change must include validation:
  - migration applies cleanly on empty DB
  - migration applies cleanly on an existing DB (when applicable)

### Rust (if used)
- Unit tests for core logic.
- Integration tests for IO and boundary behavior.

## Documentation Requirements

- Update docs when behavior changes (especially truth policy, determinism rules, query semantics).
- Public functions / modules must have docstrings (Python) or doc comments (Rust).
- Prefer docs that answer:
  - what it does
  - how it behaves in edge cases
  - how to verify it works

## Style Rules

- Meaningful names, no cryptic abbreviations.
- Keep functions small and single-purpose.
- Avoid “God modules.”
- Do not add configuration options unless they’re required; complexity has a cost.

## Security

- Secrets only via environment variables or secret managers.
- Never log secrets, tokens, or PII.
- Validate inputs at boundaries (API/CLI), reject invalid data early.

## Before You Open a PR (Required)

Run the repo’s standard checks. At minimum:
- formatting and linting
- unit/integration tests
- any perf harness required for query-path changes

PR must include:
- tests for new/changed behavior
- docs updates if semantics changed
- issue link and a clear description

## If You’re an AI Coding Agent

- Do not guess schema semantics: confirm by reading the schema/migrations and existing tests.
- Do not introduce “helpful” behavior that changes outputs unless explicitly requested.
- Prefer the smallest change that is correct, tested, and documented.
- Leave the codebase cleaner than you found it.
