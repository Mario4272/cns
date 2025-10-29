import os
import uuid

import psycopg

DEFAULT_ADMIN_DSN = "dbname=postgres user=cns password=cns host=127.0.0.1 port=5433"
DEFAULT_TEMPLATE_DB = "cns_template"

ADMIN_DSN = os.getenv("CNS_ADMIN_DSN", DEFAULT_ADMIN_DSN)
TEMPLATE_DB = os.getenv("CNS_TEMPLATE_DB", DEFAULT_TEMPLATE_DB)


def _admin_conn() -> psycopg.Connection:
    cx = psycopg.connect(ADMIN_DSN)
    cx.autocommit = True
    return cx


def ensure_template_exists(seed_dbname: str):
    with _admin_conn() as cx, cx.cursor() as cur:
        _terminate_db(cur, TEMPLATE_DB)
        cur.execute(f"DROP DATABASE IF EXISTS {TEMPLATE_DB}")
        cur.execute(f"CREATE DATABASE {TEMPLATE_DB} TEMPLATE {seed_dbname}")


def make_ephemeral_db() -> str:
    name = f"cns_test_{uuid.uuid4().hex[:8]}"
    with _admin_conn() as cx, cx.cursor() as cur:
        cur.execute(f"CREATE DATABASE {name} TEMPLATE {TEMPLATE_DB}")
    return _dsn_for(name)


def drop_db(name: str):
    with _admin_conn() as cx, cx.cursor() as cur:
        _terminate_db(cur, name)
        cur.execute(f"DROP DATABASE IF EXISTS {name}")


def _terminate_db(cur: psycopg.Cursor, name: str):
    cur.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
        """,
        (name,),
    )


def _dsn_for(dbname: str) -> str:
    parts = [p for p in ADMIN_DSN.split() if not p.startswith("dbname=")]
    parts.append(f"dbname={dbname}")
    return " ".join(parts)
