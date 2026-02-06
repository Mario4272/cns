# CNS Rust Agent Guidelines

This document defines mandatory Rust quality rules for CNS contributors and coding agents.

## Non-negotiables
- No `unwrap()` in library code (use `Result` + `thiserror`; `expect()` only for invariants).
- `cargo fmt --check`, `cargo clippy -- -D warnings`, and `cargo test` must pass before PR.
- Prefer deterministic behavior: stable ordering in queries and traversals (explicit `ORDER BY` + tie-breaks).
- Avoid unnecessary allocation; prefer borrowing; use `Vec::with_capacity()` when sizing is known.
- Document all public items with rustdoc including errors.
- No debug prints or committed logs.

## Performance / correctness
- Favor O(n) over O(n^2) where reasonable; measure before “clever”.
- Use `rayon` only for CPU-bound parallelism and only when benchmarks justify it.
- No `unsafe` without written safety invariants and review.

## PR checklist (required)
- [ ] fmt/clippy/tests pass locally
- [ ] determinism preserved (explicit ordering when applicable)
- [ ] public API changes documented
- [ ] new logic has unit tests
