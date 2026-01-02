from __future__ import annotations

"""Initialize base CNS DB and create/refresh cns_template for tests.

This script is meant to be a single deterministic entrypoint that:
- Ensures the base "cns" database exists and has the CNS schema.
- Seeds demo data (FrameworkX TLS cutover) via cns_py.demo.ingest.
- Seeds a deterministic FrameworkY contradiction fixture.
- Creates or replaces the "cns_template" database as a clone of "cns".

Usage (from repo root, with .venv activated):

    python scripts/init_template_db.py

"""

from dataclasses import dataclass  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import psycopg  # noqa: E402
from dateutil.tz import UTC  # noqa: E402

from cns_py.storage.db import DbConfig, get_conn  # noqa: E402


@dataclass
class AdminConnConfig:
    host: str
    port: int
    user: str
    password: str


def _admin_connect(dbname: str) -> psycopg.Connection:
    cfg = DbConfig()
    admin = AdminConnConfig(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
    )
    return psycopg.connect(
        host=admin.host,
        port=admin.port,
        user=admin.user,
        password=admin.password,
        dbname=dbname,
        autocommit=True,
    )


def ensure_base_db() -> None:
    """Ensure the base "cns" database exists.

    We connect to the postgres maintenance DB and create cns if missing.
    """

    cfg = DbConfig()
    with _admin_connect("postgres") as conn:  # type: ignore[call-arg]
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (cfg.dbname,))
            if cur.fetchone():
                return
            cur.execute(f"CREATE DATABASE {cfg.dbname}")


def init_schema_and_demo() -> None:
    """Initialize CNS schema and seed demo data in the base DB."""

    # Reuse existing CLI entrypoints to avoid duplicating schema logic.
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    py = sys.executable

    # Initialize schema (idempotent).
    subprocess.run([py, "-m", "cns_py.storage.db", "--init"], check=True, cwd=repo_root)

    # Seed demo data (FrameworkX TLS cutover).
    subprocess.run([py, "-m", "cns_py.demo.ingest"], check=True, cwd=repo_root)


def seed_frameworky_contradiction() -> None:
    """Seed deterministic TestFrameworkY contradiction into the base DB."""

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean any prior test data for this fixture.
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN ("
                " SELECT f.id FROM fibers f "
                " JOIN atoms a_src ON a_src.id=f.src "
                " JOIN atoms a_dst ON a_dst.id=f.dst "
                " WHERE a_src.label LIKE 'TestFrameworkY' OR a_dst.label LIKE 'TestTLS%')"
            )
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN ("
                " SELECT a.id FROM atoms a WHERE label LIKE 'TestFrameworkY' "
                " OR label LIKE 'TestTLS%')"
            )
            cur.execute(
                "DELETE FROM fibers USING atoms a_src, atoms a_dst "
                " WHERE a_src.id=fibers.src AND a_dst.id=fibers.dst "
                " AND (a_src.label LIKE 'TestFrameworkY' OR a_dst.label LIKE 'TestTLS%')"
            )
            cur.execute(
                "DELETE FROM atoms WHERE label LIKE 'TestFrameworkY' OR label LIKE 'TestTLS%'"
            )

            # Create atoms.
            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Entity", "TestFrameworkY", "A test security framework"),
            )
            framework_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestTLS1.2", "TLS version 1.2"),
            )
            tls12_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestTLS1.3", "TLS version 1.3"),
            )
            tls13_id = cur.fetchone()[0]

            now = datetime.now(tz=UTC)
            past = now - timedelta(days=60)
            future = now + timedelta(days=60)

            # Fiber 1: TLS1.2 across a wide window, confidence NULL (to be treated as lowest).
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls12_id, "supports_tls"),
            )
            fiber1_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to,
                                    belief, provenance)
                VALUES ('fiber', %s, %s, %s, %s, %s)
                """,
                (
                    fiber1_id,
                    past,
                    future,
                    None,  # NULL belief
                    "{}",
                ),
            )

            # Fiber 2: TLS1.3 overlapping, higher confidence.
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls13_id, "supports_tls"),
            )
            fiber2_id = cur.fetchone()[0]

            overlap_start = now - timedelta(days=30)
            overlap_end = future + timedelta(days=30)

            cur.execute(
                """
                INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to,
                                    belief, provenance)
                VALUES ('fiber', %s, %s, %s, %s, %s)
                """,
                (
                    fiber2_id,
                    overlap_start,
                    overlap_end,
                    0.9,
                    "{}",
                ),
            )


def recreate_template() -> None:
    """Drop and recreate cns_template as a clone of cns."""

    cfg = DbConfig()
    with _admin_connect("postgres") as conn:  # type: ignore[call-arg]
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                ("cns_template",),
            )
            cur.execute("DROP DATABASE IF EXISTS cns_template")
            cur.execute(f"CREATE DATABASE cns_template TEMPLATE {cfg.dbname}")


def main() -> int:
    ensure_base_db()
    init_schema_and_demo()
    seed_frameworky_contradiction()
    recreate_template()
    print("[init_template_db] cns and cns_template initialized successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
