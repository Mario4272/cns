# CNS Makefile

SHELL := /bin/sh
DC := docker compose -f docker/docker-compose.yml

.PHONY: up down logs psql init-db test verify tap bench e2e

up:
	$(DC) up -d

down:
	$(DC) down

logs:
	$(DC) logs -f

psql:
	$(DC) exec db psql -U cns -d cns

init-db:
	python -m cns_py.storage.db --init

# Phase 0A: QA targets (lightweight placeholders; CI will wire full steps)
test:
	. ./.venv/Scripts/activate && python -m pytest -q

verify:
	@echo "[verify] lint (ruff)"
	ruff check . || true
	@echo "[verify] format (black --check)"
	black --check . || true
	@echo "[verify] typecheck (mypy)"
	mypy cns_py || true
	@echo "[verify] tests (pytest)"
	. ./.venv/Scripts/activate && python -m pytest -q

tap:
	@echo "[tap] pgTAP placeholder (see tests_pg/)"

bench:
	@echo "[bench] not implemented yet (criterion/microbench placeholders)"

e2e:
	@echo "[e2e] Playwright demo placeholder"
