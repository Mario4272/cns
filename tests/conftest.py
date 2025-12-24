import os
import subprocess
import sys
import time

import psycopg
import pytest
from admin_db import drop_db, ensure_template_exists, make_ephemeral_db

from cns_py.storage.db import DbConfig

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, os.pardir))


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO)


@pytest.fixture(scope="session", autouse=True)
def seed_template_db():
    # Skip Docker Compose if running in CI (GitHub Actions provides postgres service)
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

    if not is_ci:
        # Clean up any existing containers first (handles port conflicts from previous runs)
        try:
            _run(["docker", "compose", "-f", "docker/docker-compose.yml", "down"])
        except subprocess.CalledProcessError:
            pass  # Ignore if nothing to clean up

        # Bring up docker services (idempotent). Retry once if docker is waking up.
        for attempt in range(2):
            try:
                _run(["docker", "compose", "-f", "docker/docker-compose.yml", "up", "-d"])
                break
            except subprocess.CalledProcessError:
                if attempt == 0:
                    time.sleep(2.0)
                else:
                    raise

        # Wait a moment for DB to accept connections
        time.sleep(1.0)

    # Wait for database to be ready (especially important in CI)
    max_retries = 10
    for i in range(max_retries):
        try:
            with psycopg.connect(
                host=DbConfig().host,
                port=DbConfig().port,
                dbname=DbConfig().dbname,
                user=DbConfig().user,
                password=DbConfig().password,
                connect_timeout=2,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                print(f"Database connection successful on attempt {i+1}")
                break
        except Exception as e:
            if i == max_retries - 1:
                raise RuntimeError(f"Database not ready after {max_retries} attempts: {e}")
            print(f"Waiting for database (attempt {i+1}/{max_retries})...")
            time.sleep(1)

    # Initialize schema and ingest demo in base DB (cns)
    py = sys.executable
    try:
        _run([py, "-m", "cns_py.storage.db", "--init"])
    except subprocess.CalledProcessError as e:
        print(f"[CONFTEST] Schema init returned non-zero: {e}; verifying existing schema...")
        with psycopg.connect(
            host=DbConfig().host,
            port=DbConfig().port,
            dbname=DbConfig().dbname,
            user=DbConfig().user,
            password=DbConfig().password,
        ) as _conn:
            with _conn.cursor() as _cur:
                # check tables exist
                _cur.execute(
                    "SELECT to_regclass('public.atoms'), "
                    "to_regclass('public.fibers'), "
                    "to_regclass('public.aspects')"
                )
                atoms_t, fibers_t, aspects_t = _cur.fetchone()
                if not (atoms_t and fibers_t and aspects_t):
                    raise
    # Ensure no unique index remains that would block duplicate-label tests
    with psycopg.connect(
        host=DbConfig().host,
        port=DbConfig().port,
        dbname=DbConfig().dbname,
        user=DbConfig().user,
        password=DbConfig().password,
    ) as _conn:
        with _conn.cursor() as _cur:
            _cur.execute("DROP INDEX IF EXISTS uniq_atoms_kind_label")
    try:
        _run([py, "-m", "cns_py.demo.ingest"])
    except subprocess.CalledProcessError as e:
        print(
            "[CONFTEST] Demo ingest returned non-zero during session seed: "
            f"{e}; verifying existing data..."
        )
        with psycopg.connect(
            host=DbConfig().host,
            port=DbConfig().port,
            dbname=DbConfig().dbname,
            user=DbConfig().user,
            password=DbConfig().password,
        ) as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "SELECT COUNT(*) FROM fibers f JOIN atoms a ON a.id=f.src "
                    "WHERE a.label='FrameworkX' AND f.predicate='supports_tls'"
                )
                atoms_ok = int(_cur.fetchone()[0]) >= 3
                _cur.execute("SELECT COUNT(*) FROM fibers WHERE predicate='supports_tls'")
                fibers_ok = int(_cur.fetchone()[0]) >= 2
                if not (atoms_ok and fibers_ok):
                    raise

    # Canonicalize demo atoms to avoid duplicate IDs across re-ingests
    with psycopg.connect(
        host=DbConfig().host,
        port=DbConfig().port,
        dbname=DbConfig().dbname,
        user=DbConfig().user,
        password=DbConfig().password,
    ) as _conn:
        with _conn.cursor() as _cur:
            for lbl in ("FrameworkX", "TLS1.2", "TLS1.3"):
                # choose canonical id (min)
                _cur.execute("SELECT MIN(id) FROM atoms WHERE label=%s", (lbl,))
                row = _cur.fetchone()
                if not row or row[0] is None:
                    continue
                canon = int(row[0])
                # repoint fibers
                _cur.execute(
                    "UPDATE fibers SET src=%s WHERE src IN ("
                    "SELECT id FROM atoms WHERE label=%s AND id<>%s)",
                    (canon, lbl, canon),
                )
                _cur.execute(
                    "UPDATE fibers SET dst=%s WHERE dst IN ("
                    "SELECT id FROM atoms WHERE label=%s AND id<>%s)",
                    (canon, lbl, canon),
                )
                # delete non-canonical atoms
                _cur.execute("DELETE FROM atoms WHERE label=%s AND id<>%s", (lbl, canon))

    # Create/refresh template DB cloned from base 'cns'
    ensure_template_exists("cns")
    yield


@pytest.fixture(scope="function", autouse=True)
def per_test_ephemeral_db(monkeypatch):
    """Each test runs against a fresh clone of the seeded template DB."""
    dsn = make_ephemeral_db()
    # Parse out dbname and set CNS_DB_NAME for app code
    dbname = next((p.split("=")[1] for p in dsn.split() if p.startswith("dbname=")), None)
    if dbname:
        monkeypatch.setenv("CNS_DB_NAME", dbname)
    # Verify demo data present; if missing (rare), seed inline
    try:
        with psycopg.connect(
            host=DbConfig().host,
            port=DbConfig().port,
            dbname=DbConfig().dbname,
            user=DbConfig().user,
            password=DbConfig().password,
        ) as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "SELECT COUNT(*) FROM fibers f JOIN atoms a ON a.id=f.src "
                    "WHERE a.label='FrameworkX' AND f.predicate='supports_tls'"
                )
                if int(_cur.fetchone()[0]) < 2:
                    from cns_py.demo import ingest as demo_ingest

                    demo_ingest.main()
    except Exception:
        pass
    yield
    if dbname:
        drop_db(dbname)
