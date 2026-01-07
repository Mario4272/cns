"""
Tests for Multi-Space Vector Indexing (Slice 9.1).
Verifies that IndexManager can handle multiple isolated vector spaces.
"""

import os

import numpy as np
import pytest

from cns_py.vector import ExactInMemoryIndex
from cns_py.vector.manager import IndexManager


@pytest.fixture
def temp_vector_path(tmp_path):
    """Provide a temp path for vector storage."""
    path = tmp_path / "vector_store" / "index"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return str(path)


@pytest.fixture
def mock_config(monkeypatch, temp_vector_path):
    """Mock config to use temp path and memory backend."""
    monkeypatch.setattr("cns_py.config.vector_index_enabled", lambda: True)
    monkeypatch.setattr("cns_py.config.vector_index_backend", lambda: "memory")
    monkeypatch.setattr("cns_py.config.vector_index_path", lambda: temp_vector_path)
    # Mock rebuild to avoid DB access
    monkeypatch.setattr(
        "cns_py.vector.manager.IndexManager.rebuild", lambda self, space="default": None
    )


def test_multi_space_isolation(mock_config):
    """Verify separate spaces contain separate data."""
    mgr = IndexManager()
    mgr.startup()

    # Create Space A and B explicitly
    mgr.indices["space_a"] = ExactInMemoryIndex()
    mgr.indices["space_b"] = ExactInMemoryIndex()

    # Mock Embeddings (using random for distinctness)
    vec_a = np.random.rand(384).astype(np.float32)
    vec_b = np.random.rand(384).astype(np.float32)

    # Load Data
    mgr.indices["space_a"].bulk_load([("doc_a", vec_a, {"label": "Apple"})])
    mgr.indices["space_b"].bulk_load([("doc_b", vec_b, {"label": "Banana"})])

    # Query Space A
    results_a = mgr.query(vec_a, k=10, space="space_a")
    assert len(results_a) == 1
    assert results_a[0][0] == "doc_a"

    # Query Space B
    results_b = mgr.query(vec_b, k=10, space="space_b")
    assert len(results_b) == 1
    assert results_b[0][0] == "doc_b"

    # Cross Query (A should not find B)
    # If we query A with vec_b, it should be empty or distinct?
    # Actually ExactInMemoryIndex returns matches if present.
    # But "doc_b" should definitely NOT be in space_a results.
    results_cross = mgr.query(vec_b, k=10, space="space_a")
    found_ids = [r[0] for r in results_cross]
    assert "doc_b" not in found_ids


def test_persistence_multiple_spaces(mock_config, temp_vector_path):
    """Verify multiple spaces are saved and loaded correctly."""
    # 1. Setup and Save
    mgr = IndexManager()
    mgr.startup()

    mgr.indices["space_x"] = ExactInMemoryIndex()
    mgr.indices["space_y"] = ExactInMemoryIndex()

    # Populate to ensure files are written
    vec = np.zeros(384, dtype=np.float32)
    mgr.indices["space_x"].bulk_load([("item_x", vec, {})])
    mgr.indices["space_y"].bulk_load([("item_y", vec, {})])

    mgr.shutdown()

    # Verify files exist
    # Expecting: {temp_path}_space_x.npz and {temp_path}_space_y.npz
    assert os.path.exists(f"{temp_vector_path}_space_x.npz")
    assert os.path.exists(f"{temp_vector_path}_space_y.npz")

    # 2. Load
    # Helper to simulate fresh start
    mgr2 = IndexManager()
    # Mocking config again just in case (fixture does it but new instance checks config)

    # Startup loads "default". We need to manually trigger loading of other spaces
    # or rely on logic if we added auto-discovery.
    # Current implementation relies on explicit access or `rebuild`.
    # BUT `startup` logic only loads "default".
    # So mgr2.indices should be empty (except default) until we access/load them.

    mgr2.startup()
    assert "default" in mgr2.indices
    assert "space_x" not in mgr2.indices

    # Manually trigger load of named spaces (emulating a Router knowing what it needs)
    loaded_x = mgr2._load_or_create_space("space_x")
    assert loaded_x is True
    assert "space_x" in mgr2.indices

    # Verify content
    results = mgr2.query(vec, k=1, space="space_x")
    assert len(results) == 1
    assert results[0][0] == "item_x"
