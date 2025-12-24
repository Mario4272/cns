from __future__ import annotations

import os
from typing import Dict, Optional

from cns_py.storage.db import DbConfig


def _with_env(overrides: Dict[str, str]) -> None:
    # Helper to update environment in-place for this process
    for k, v in overrides.items():
        os.environ[k] = v


def _restore_env(snapshot: Dict[str, Optional[str]]) -> None:
    for k, v in snapshot.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_dbconfig_uses_defaults_when_env_missing():
    # Snapshot and clear CNS_DB_* variables
    keys = ["CNS_DB_HOST", "CNS_DB_PORT", "CNS_DB_NAME", "CNS_DB_USER", "CNS_DB_PASSWORD"]
    snapshot: Dict[str, Optional[str]] = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ.pop(k, None)

    try:
        cfg = DbConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 5433
        assert cfg.dbname == "cns"
        assert cfg.user == "cns"
        assert cfg.password == "cns"  # pragma: allowlist secret (test default password)
    finally:
        _restore_env(snapshot)


def test_dbconfig_reads_values_from_env():
    keys = ["CNS_DB_HOST", "CNS_DB_PORT", "CNS_DB_NAME", "CNS_DB_USER", "CNS_DB_PASSWORD"]
    snapshot: Dict[str, Optional[str]] = {k: os.environ.get(k) for k in keys}

    overrides = {
        "CNS_DB_HOST": "db.test.local",
        "CNS_DB_PORT": "6543",
        "CNS_DB_NAME": "testdb",
        "CNS_DB_USER": "tester",
        "CNS_DB_PASSWORD": "secret",  # pragma: allowlist secret
    }
    _with_env(overrides)

    try:
        cfg = DbConfig()
        assert cfg.host == "db.test.local"
        assert cfg.port == 6543
        assert cfg.dbname == "testdb"
        assert cfg.user == "tester"
        assert cfg.password == "secret"  # pragma: allowlist secret
    finally:
        _restore_env(snapshot)
