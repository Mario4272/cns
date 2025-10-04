# CNS Makefile

SHELL := /bin/sh
DC := docker compose -f docker/docker-compose.yml

.PHONY: up down logs psql init-db

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
