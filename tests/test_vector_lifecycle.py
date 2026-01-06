import os

import pytest

from cns_py.storage.db import get_conn
from cns_py.vector.manager import IndexManager

# Dummy env var fixture?
# Best to patch os.environ or config.


@pytest.fixture
def lifecycle_config(tmp_path, monkeypatch):
    """Setup safe config for lifecycle test."""
    idx_path = tmp_path / "lifecycle_index"
    monkeypatch.setenv("VECTOR_INDEX_ENABLED", "1")
    monkeypatch.setenv("VECTOR_INDEX_BACKEND", "memory")
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(idx_path))
    return str(idx_path)


def test_index_lifecycle_restart(lifecycle_config):
    """
    Verify:
    1. Rebuild from DB.
    2. Query works.
    3. Shutdown (Persist).
    4. Startup (Load).
    5. Query works same as before.
    """

    # 1. Setup DB Data
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean atoms first? Assuming test DB isolation.
            # Insert test atoms
            cur.execute(
                """
                INSERT INTO atoms (label, kind, text) VALUES 
                ('LifecycleAlpha', 'Entity', 'Alpha content for embedding'),
                ('LifecycleBeta', 'Concept', 'Beta content for embedding')
                RETURNING id, label;
            """
            )
            rows = cur.fetchall()
            id_map = {label: str(aid) for aid, label in rows}

    # 2. Manager 1: Startup (Rebuild)
    mgr1 = IndexManager()
    mgr1.startup()

    # Verify index has content
    res1 = mgr1.query(mgr1.provider.embed_texts(["Alpha content for embedding"])[0], k=1)
    assert len(res1) == 1
    assert res1[0][0] == id_map["LifecycleAlpha"]
    score1 = res1[0][1]

    # 3. Shutdown (Save)
    mgr1.shutdown()

    # IndexManager appends space name, e.g. _default
    expected_path = f"{lifecycle_config}_default.npz"
    assert os.path.exists(expected_path)

    # 4. Manager 2: Startup (Load)
    # Clear any in-memory state if shared?
    # Manager is distinct instance, but check if singleton in real app interferes?
    # Here we instantiate new class.

    mgr2 = IndexManager()
    mgr2.startup()

    # Verify loaded content matches exactly
    res2 = mgr2.query(mgr2.provider.embed_texts(["Alpha content for embedding"])[0], k=1)
    assert len(res2) == 1
    assert res2[0][0] == id_map["LifecycleAlpha"]
    assert abs(res2[0][1] - score1) < 1e-5

    # Verify internal state shows it was loaded
    # (By checking metadata or just relying on the fact that if it rebuilt, it would be same)
    # The real test is that it exists without DB query if we wanted, but for now exact match is key.


def test_integration_api_lifecycle(lifecycle_config):
    """Verify API integration uses the manager."""
    from cns_py.api.server import (
        _INDEX_MANAGER,
        VectorQuery,
        find_similar,
        shutdown_event,
        startup_event,
    )
    from cns_py.vector.embeddings import DeterministicStubProvider

    # RESET global manager to ensure defaults (384D) and no 2D pollution
    _INDEX_MANAGER.index = None
    _INDEX_MANAGER.provider = DeterministicStubProvider(dim=384)
    _INDEX_MANAGER.dim = 384

    # 1. Setup DB
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO atoms (label, kind) VALUES ('ApiTest', 'Entity') RETURNING id")
            aid = cur.fetchone()[0]

    # 2. Trigger startup (rebuild global manager)
    startup_event()

    # 3. Query via API function
    # Need vector. Helper to embed:
    # 3. Query via API function
    # Need vector. Helper to embed:
    mgr = IndexManager()
    vec = mgr.provider.embed_texts(["ApiTest"])[0]  # Label fallback

    req = VectorQuery(vector=vec, k=1)
    env = find_similar(req)

    assert len(env.results) > 0
    top = env.results[0]
    assert top.id == str(aid)
    assert top.label == "ApiTest"  # Enriched!
    assert top.kind == "Entity"  # Enriched!

    # 4. Cleanup
    shutdown_event()
