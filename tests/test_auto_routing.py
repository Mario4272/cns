"""
Integration tests for Auto-Routing (Slice 9.2).
"""

import numpy as np
import pytest

from cns_py.vector import ExactInMemoryIndex
from cns_py.vector.manager import IndexManager


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    path = tmp_path / "vector_store" / "index"
    monkeypatch.setattr("cns_py.config.vector_index_enabled", lambda: True)
    monkeypatch.setattr("cns_py.config.vector_index_backend", lambda: "memory")
    monkeypatch.setattr("cns_py.config.vector_index_path", lambda: str(path))
    # Mock rebuild to avoid DB access
    monkeypatch.setattr(
        "cns_py.vector.manager.IndexManager.rebuild", lambda self, space="default": None
    )


def test_auto_routing_flow(mock_config):
    """
    Verify that space='auto' routes queries to appropriate spaces
    and merges results.
    """
    mgr = IndexManager()
    mgr.startup()

    # Setup Spaces
    mgr.indices["code"] = ExactInMemoryIndex()
    mgr.indices["default"] = ExactInMemoryIndex()

    # Create distinct vectors
    # vector A: [1, 0, ...] -> target for Code query
    vec_code = np.zeros(384, dtype=np.float32)
    vec_code[0] = 1.0

    # vector B: [0, 1, ...] -> target for Default query
    vec_default = np.zeros(384, dtype=np.float32)
    vec_default[1] = 1.0

    # Populate
    mgr.indices["code"].bulk_load([("func_def", vec_code, {"label": "def foo()"})])
    mgr.indices["default"].bulk_load([("recipe", vec_default, {"label": "Pie Recipe"})])

    # 1. Query "def bar" (Code-like)
    # The router should prefer "code".
    # We query with vec_code to ensure high similarity if routed to code space.
    # Note: HeuristicRouter returns [("code", 0.8), ("default", 0.2)]
    # Sim in Code space: 1.0 * 0.8 = 0.8
    # Sim in Default: 0.0 * 0.2 = 0.0
    results = mgr.query(vec_code, k=5, space="auto", query_text="def bar()")

    assert len(results) > 0
    top_id, top_score = results[0]
    assert top_id == "func_def"
    # Score should be significantly weighted
    assert top_score > 0.5

    # 2. Query "baking" (Default-like)
    # Router returns [("default", 1.0)]
    # Query with vec_default
    results = mgr.query(vec_default, k=5, space="auto", query_text="baking")

    assert len(results) > 0
    top_id, top_score = results[0]
    assert top_id == "recipe"
    assert top_score > 0.9  # 1.0 * 1.0 approx

    # 3. Verify Fallback (No text)
    # Should route to default check
    # Query with vec_default (present in default space)
    results = mgr.query(vec_default, k=5, space="auto")  # No query_text
    assert len(results) > 0
    assert results[0][0] == "recipe"
