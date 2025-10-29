# QA Guide: Reproducing CI Locally

This document explains how to reproduce all CI checks locally before pushing.

---

## Prerequisites

- Python 3.10, 3.11, or 3.12
- Docker + Docker Compose
- PostgreSQL client (`psql`)
- Git

---

## Quick Start

```bash
# 1. Start infrastructure
make up

# 2. Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Run all checks
make verify
```

---

## Individual CI Steps

### 1. Coverage (≥85% enforced)

**CI Command:**
```bash
pytest -q \
  --cov=cns_py \
  --cov-report=xml \
  --cov-report=html \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=85 \
  --hypothesis-show-statistics \
  --hypothesis-seed=123456
```

**Local Reproduction:**
```bash
# Set environment variables
export CNS_DB_HOST=127.0.0.1
export CNS_DB_PORT=5433
export CNS_DB_NAME=cns
export CNS_DB_USER=cns
export CNS_DB_PASSWORD=cns
export CNS_VECTOR_DIMS=1536

# Run tests with coverage
pytest -q \
  --cov=cns_py \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=85

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Artifacts:**
- `coverage.xml` — Machine-readable coverage data
- `htmlcov/` — Human-readable HTML report

**Common Failures:**
- **Coverage below 85%**: Add tests for uncovered code or mark as `# pragma: no cover` with justification
- **Import errors**: Ensure all dependencies installed with `pip install -e ".[dev]"`

---

### 2. pgTAP (Schema Invariants)

**CI Command:**
```bash
psql "postgres://cns:cns@127.0.0.1:5433/cns" -f tests_pg/pg_tap_smoke.sql  # pragma: allowlist secret
```

**Local Reproduction:**
```bash
# Ensure database is running
make up

# Run pgTAP tests
psql "postgres://cns:cns@127.0.0.1:5433/cns" -f tests_pg/pg_tap_smoke.sql  # pragma: allowlist secret

# Or use pg_prove (if installed)
pg_prove -U cns -h 127.0.0.1 -p 5433 -d cns tests_pg/*.sql
```

**Artifacts:**
- `pg_tap_results.tap` — TAP format test results

**Common Failures:**
- **Extension not found**: Run `python -m cns_py.storage.db --init` to initialize schema
- **Connection refused**: Ensure `make up` completed successfully and Postgres is healthy

---

### 3. Perf Smoke (P95 ≤ 500ms, P99 ≤ 900ms)

**CI Command:**
```bash
python scripts/perf_smoke.py --iters 300 --warmup 50 --p95-budget-ms 500 --p99-budget-ms 900
```

**Local Reproduction:**
```bash
# Set environment variables
export CNS_DB_HOST=127.0.0.1
export CNS_DB_PORT=5433
export CNS_DB_NAME=cns
export CNS_DB_USER=cns
export CNS_DB_PASSWORD=cns

# Initialize and seed database
python -m cns_py.storage.db --init
python -m cns_py.demo.ingest

# Run perf smoke test
python scripts/perf_smoke.py --iters 300 --warmup 50 --p95-budget-ms 500 --p99-budget-ms 900
```

**Artifacts:**
- `perf_last_explain.json` — EXPLAIN output from last query

**Common Failures:**
- **P95 > 500ms**: Database not warmed up, or hardware too slow. Try increasing `--warmup` or running on faster hardware.
- **No data**: Run `python -m cns_py.demo.ingest` to seed demo data.
- **Connection error**: Ensure database is running and environment variables are set.

---

### 4. Property Tests (Hypothesis)

**CI Command:**
```bash
pytest tests/test_parser_property.py -q --hypothesis-show-statistics --hypothesis-seed=123456
```

**Local Reproduction:**
```bash
# Run property tests
pytest tests/test_parser_property.py -q --hypothesis-show-statistics

# Run with specific seed for reproducibility
pytest tests/test_parser_property.py -q --hypothesis-seed=123456

# Run with more examples (slower but more thorough)
pytest tests/test_parser_property.py -q --hypothesis-profile=ci
```

**Artifacts:**
- `property_stats.txt` — Hypothesis statistics (if enabled)

**Common Failures:**
- **Shrinking timeout**: Increase deadline with `@settings(deadline=None)` or `deadline=timedelta(milliseconds=500)`
- **Flaky test**: Use `--hypothesis-seed` to reproduce, then fix the root cause

---

### 5. Contradiction Detection Integration Tests

**CI Command:**
```bash
pytest tests/test_contradiction_integration.py -q
```

**Local Reproduction:**
```bash
# Set environment variables
export CNS_DB_HOST=127.0.0.1
export CNS_DB_PORT=5433
export CNS_DB_NAME=cns
export CNS_DB_USER=cns
export CNS_DB_PASSWORD=cns

# Run contradiction tests
pytest tests/test_contradiction_integration.py -q -v

# Run with EXPLAIN artifact capture
pytest tests/test_contradiction_integration.py -q --tb=short
```

**Artifacts:**
- `explain/*.txt` — EXPLAIN output on failure (if configured)

**Common Failures:**
- **Contradiction not detected**: Check temporal overlap logic in `cns_py/cql/contradict.py`
- **False positives**: Verify non-overlapping ranges don't trigger detection

---

### 6. Linting & Formatting

**CI Commands:**
```bash
ruff check .
black --check .
mypy cns_py
```

**Local Reproduction:**
```bash
# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Format check with black
black --check .

# Auto-format
black .

# Type check with mypy
mypy cns_py
```

**Common Failures:**
- **Import order**: Run `ruff check . --fix` to auto-sort
- **Line too long**: Break into multiple lines or use `# noqa: E501` with justification
- **Type errors**: Add type hints or use `# type: ignore` with comment explaining why

---

## Pre-Commit Hooks

Install pre-commit hooks to catch issues before committing:

```bash
pip install pre-commit
pre-commit install
```

Now hooks will run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

---

## Environment Variables

All tests require these environment variables:

```bash
export CNS_DB_HOST=127.0.0.1
export CNS_DB_PORT=5433
export CNS_DB_NAME=cns
export CNS_DB_USER=cns
export CNS_DB_PASSWORD=cns
export CNS_VECTOR_DIMS=1536
```

Or create a `.env` file (not committed):

```bash
CNS_DB_HOST=127.0.0.1
CNS_DB_PORT=5433
CNS_DB_NAME=cns
CNS_DB_USER=cns
CNS_DB_PASSWORD=cns
CNS_VECTOR_DIMS=1536
```

Then load with:

```bash
export $(cat .env | xargs)
```

---

## Troubleshooting

### Database Connection Issues

**Symptom:** `psycopg.OperationalError: connection refused`

**Solutions:**
1. Ensure Docker is running: `docker ps`
2. Start infrastructure: `make up`
3. Check Postgres health: `docker compose -f docker/docker-compose.yml ps`
4. Verify port: `lsof -i :5433` (macOS/Linux) or `netstat -ano | findstr :5433` (Windows)

### Coverage Below Threshold

**Symptom:** `FAIL Required test coverage of 85% not reached. Total coverage: 82.5%`

**Solutions:**
1. Add tests for uncovered code
2. Mark intentionally uncovered code with `# pragma: no cover`
3. Check coverage report: `open htmlcov/index.html`

### Perf Test Timeout

**Symptom:** `P95 > 500ms`

**Solutions:**
1. Increase warmup iterations: `--warmup 100`
2. Check database is local (not remote)
3. Ensure no other processes competing for resources
4. Run on faster hardware or adjust budget: `--p95-budget-ms 1000`

### Property Test Failures

**Symptom:** `Falsifying example: test_parse_label_roundtrip(label='...')`

**Solutions:**
1. Reproduce with seed: `--hypothesis-seed=<seed_from_output>`
2. Fix the root cause (usually parser bug)
3. Add explicit test case for the failing example

### pgTAP Not Found

**Symptom:** `ERROR: extension "pgtap" is not available`

**Solutions:**
1. Use pgvector image (includes pgTAP): `pgvector/pgvector:pg16`
2. Or install pgTAP manually in Postgres container

---

## CI Matrix

CI runs on:
- **Python**: 3.10, 3.11, 3.12
- **PostgreSQL**: 15, 16

To test specific combinations locally:

```bash
# Python 3.11 + Postgres 16
pyenv local 3.11
docker compose -f docker/docker-compose.yml down
# Edit docker-compose.yml to use pg16
docker compose -f docker/docker-compose.yml up -d
make verify
```

---

## Artifacts

CI uploads these artifacts (retained 14 days):

- `coverage-reports-*` — Coverage XML + HTML
- `pgtap-results-*` — pgTAP TAP output
- `perf-artifacts-*` — Performance EXPLAIN JSON
- `sbom-*` — Software Bill of Materials (CycloneDX)

Download from GitHub Actions run page → "Artifacts" section.

---

## Quick Reference

| Check | Command | Expected Result |
|-------|---------|-----------------|
| **All** | `make verify` | All checks pass |
| **Tests** | `make test` | All tests pass, coverage ≥85% |
| **Lint** | `ruff check .` | No errors |
| **Format** | `black --check .` | No changes needed |
| **Types** | `mypy cns_py` | No type errors |
| **pgTAP** | `make tap` | All schema tests pass |
| **Perf** | `python scripts/perf_smoke.py` | P95 ≤ 500ms |

---

## Getting Help

- **CI failing?** Check the "Artifacts" section for detailed logs
- **Local tests failing?** Ensure environment variables are set
- **Still stuck?** Open an issue with:
  - CI run URL
  - Local reproduction steps
  - Error messages
  - Environment details (`python --version`, `docker --version`)
