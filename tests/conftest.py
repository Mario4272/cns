import os
import subprocess
import sys
import time

import psycopg
import pytest

from cns_py.storage.db import DbConfig

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, os.pardir))


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO)


@pytest.fixture(scope="session", autouse=True)
def ensure_db_and_demo_ready():
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

    # Initialize schema and ingest demo using the current Python interpreter
    py = sys.executable
    try:
        _run([py, "-m", "cns_py.storage.db", "--init"])
    except subprocess.CalledProcessError as e:
        # If already initialized, continue
        print(f"Schema init returned non-zero (may already exist): {e}")
        pass

    # Ingest demo data - fail loudly if this doesn't work
    try:
        _run([py, "-m", "cns_py.demo.ingest"])
    except subprocess.CalledProcessError as e:
        print(f"FATAL: Demo ingest failed: {e}")
        raise

    # Verify demo data was actually inserted
    with psycopg.connect(
        host=DbConfig().host,
        port=DbConfig().port,
        dbname=DbConfig().dbname,
        user=DbConfig().user,
        password=DbConfig().password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM atoms")
            atom_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM fibers")
            fiber_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM aspects")
            aspect_count = cur.fetchone()[0]
            print(
                f"[CONFTEST] Data verification: {atom_count} atoms, "
                f"{fiber_count} fibers, {aspect_count} aspects"
            )

            # Debug: Show actual aspect data
            cur.execute(
                "SELECT subject_kind, subject_id, valid_from, valid_to, belief "
                "FROM aspects ORDER BY subject_id"
            )
            print("[CONFTEST] Aspect data:")
            for row in cur.fetchall():
                print(f"  {row}")

            # Debug: Show fibers with their atoms
            cur.execute(
                "SELECT f.id, a_src.label, f.predicate, a_dst.label "
                "FROM fibers f "
                "JOIN atoms a_src ON a_src.id = f.src "
                "JOIN atoms a_dst ON a_dst.id = f.dst "
                "ORDER BY f.id"
            )
            print("[CONFTEST] Fiber data:")
            for row in cur.fetchall():
                print(f"  Fiber {row[0]}: {row[1]} --{row[2]}--> {row[3]}")

            # Debug: Test the actual JOIN that's failing
            cur.execute(
                "SELECT f.id, a_src.label, f.predicate, a_dst.label, "
                "asp.valid_from, asp.valid_to, asp.belief "
                "FROM fibers f "
                "JOIN atoms a_src ON a_src.id = f.src "
                "JOIN atoms a_dst ON a_dst.id = f.dst "
                "JOIN aspects asp ON asp.subject_kind='fiber' AND asp.subject_id=f.id "
                "WHERE a_src.label = 'FrameworkX'"
            )
            print("[CONFTEST] JOIN test (FrameworkX fibers with aspects):")
            for row in cur.fetchall():
                print(
                    f"  Fiber {row[0]}: {row[1]} --{row[2]}--> {row[3]}, "
                    f"valid_from={row[4]}, valid_to={row[5]}, belief={row[6]}"
                )

            if atom_count == 0:
                raise RuntimeError("FATAL: Demo ingest succeeded but no atoms in database!")

    yield
