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

    yield
