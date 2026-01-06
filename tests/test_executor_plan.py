"""
Integration tests for Executor (Slice 10.1).
"""
import pytest
from typing import List, Any
from unittest.mock import MagicMock

from cns_py.planner.plan import RetrievalPlan, ExactQueryStep, VectorSearchStep
from cns_py.planner.executor import Executor
from cns_py.vector.manager import IndexManager
from cns_py.vector.embeddings import DeterministicStubProvider

@pytest.fixture
def mock_manager():
    mgr = MagicMock(spec=IndexManager)
    mgr.provider = DeterministicStubProvider(dim=384)
    # Mock query return
    mgr.query.return_value = [("doc_1", 0.95)]
    return mgr

def test_executor_runs_steps(mock_manager):
    executor = Executor(mock_manager)
    
    # Create manual plan
    plan = RetrievalPlan(
        query_raw="test",
        steps=[
            ExactQueryStep(atom_id="123"),
            VectorSearchStep(query_text="test", space="default")
        ]
    )
    
    findings = executor.execute(plan)
    
    assert len(findings.results) == 2
    
    # Check Exact Result (Stubbed in Executor)
    res0 = findings.results[0]
    assert res0.step_type == "exact"
    assert res0.items[0]["id"] == "123"
    
    # Check Vector Result (Mocked Manager)
    res1 = findings.results[1]
    assert res1.step_type == "vector"
    assert res1.items[0] == ("doc_1", 0.95)
    
    # Verify manager called
    mock_manager.query.assert_called_once()
