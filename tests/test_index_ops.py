"""
Tests for Index Ops (Slice 11.3).
Verifies status reporting and rebuild triggering.
"""
from unittest.mock import MagicMock, patch

import pytest

from cns_py.api.server import RebuildRequest, index_rebuild_endpoint, index_status_endpoint
from cns_py.vector.manager import IndexManager


@pytest.fixture
def mock_mgr():
    with patch("cns_py.api.server._INDEX_MANAGER") as m:
        # Defaults
        m.get_status.return_value = {
            "enabled": True, 
            "backend": "memory", 
            "spaces": {"default": {"count": 10}}
        }
        yield m

def test_status_endpoint(mock_mgr):
    status = index_status_endpoint()
    assert status["enabled"] is True
    assert status["backend"] == "memory"
    assert "default" in status["spaces"]

def test_rebuild_requires_confirm():
    req = RebuildRequest(confirm=False)
    # Should raise HTTP 400
    try:
        index_rebuild_endpoint(req)
        pytest.fail("Should have raised HTTPException")
    except Exception as e:
        assert "400" in str(e) or "Must confirm" in str(e)

def test_rebuild_triggers_manager(mock_mgr):
    req = RebuildRequest(confirm=True, space="test_space")
    resp = index_rebuild_endpoint(req)
    
    mock_mgr.rebuild.assert_called_once_with(space="test_space")
    assert resp["status"] == "success"

def test_real_manager_status_structure():
    # Integration test with real class (but maybe empty)
    mgr = IndexManager()
    mgr.indices["default"] = MagicMock()
    mgr.indices["default"].ids = [1, 2, 3] # Mock memory index attribute
    
    status = mgr.get_status()
    assert status["enabled"] is not None
    assert status["spaces"]["default"]["count"] == 3
