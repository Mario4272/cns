import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, os.pardir))


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO)


@pytest.fixture(scope="session", autouse=True)
def ensure_db_and_demo_ready():
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

    # Initialize schema and ingest demo using the current Python interpreter
    py = sys.executable
    try:
        _run([py, "-m", "cns_py.storage.db", "--init"])
    except subprocess.CalledProcessError:
        # If already initialized, continue
        pass
    _run([py, "-m", "cns_py.demo.ingest"])

    yield
