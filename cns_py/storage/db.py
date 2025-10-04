import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional

import psycopg


@dataclass
class DbConfig:
    host: str = os.getenv("CNS_DB_HOST", "127.0.0.1")
    port: int = int(os.getenv("CNS_DB_PORT", "5433"))
    dbname: str = os.getenv("CNS_DB_NAME", "cns")
    user: str = os.getenv("CNS_DB_USER", "cns")
    password: str = os.getenv("CNS_DB_PASSWORD", "cns")


def get_conn(cfg: Optional[DbConfig] = None) -> psycopg.Connection:
    cfg = cfg or DbConfig()
    return psycopg.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.dbname,
        user=cfg.user,
        password=cfg.password,
        autocommit=True,
    )


SCHEMA_SQL = r"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS atoms (
  id BIGSERIAL PRIMARY KEY,
  kind TEXT NOT NULL,            -- Entity | Event | Rule | Program
  label TEXT NOT NULL,           -- human label or canonical name
  text TEXT,                     -- optional long text
  symbol JSONB,                  -- optional symbolic form (AST/Datalog/SMT)
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Directed typed edges between atoms
CREATE TABLE IF NOT EXISTS fibers (
  id BIGSERIAL PRIMARY KEY,
  src BIGINT NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
  dst BIGINT NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
  predicate TEXT NOT NULL,       -- relation type
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Aspects associated to atoms or fibers (one row per subject+aspect type)
CREATE TABLE IF NOT EXISTS aspects (
  id BIGSERIAL PRIMARY KEY,
  subject_kind TEXT NOT NULL CHECK (subject_kind IN ('atom','fiber')),
  subject_id BIGINT NOT NULL,
  -- bitemporal tape
  valid_from TIMESTAMPTZ,
  valid_to   TIMESTAMPTZ,
  observed_at TIMESTAMPTZ DEFAULT now(),
  -- belief
  belief REAL,                   -- 0..1 confidence
  -- provenance
  provenance JSONB,              -- {source:..., evidence:...}
  -- vectors (multi-space); use separate table for real workloads; simple here
  embedding vector(384),
  UNIQUE(subject_kind, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_fibers_src ON fibers(src);
CREATE INDEX IF NOT EXISTS idx_fibers_dst ON fibers(dst);
CREATE INDEX IF NOT EXISTS idx_aspects_subject ON aspects(subject_kind, subject_id);
"""


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
    print("Initialized schema (atoms, fibers, aspects) and pgvector extension.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="CNS DB utilities")
    parser.add_argument("--init", action="store_true", help="Initialize schema")
    args = parser.parse_args(argv)

    if args.init:
        init_db()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
