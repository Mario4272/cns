"""
Tests for Rule Registry & API (Slice 11.2).
Verifies:
1. Logic can load manifest.
2. Logic can run rule via WASM.
3. API endpoints (mocked) work as expected.
"""
import pytest

from cns_py.api.server import RunRuleRequest, run_rule_endpoint
from cns_py.rules import RuleRegistry


def test_registry_load_manifest():
    # Should autoload default
    registry = RuleRegistry()
    rules = registry.list_rules()
    assert len(rules) >= 2
    
    ids = [r.id for r in rules]
    assert "tls_compliance" in ids
    assert "contradiction_marker" in ids

def test_run_rule_logic():
    registry = RuleRegistry()
    # Mock context for tls_compliance
    ctx = {"trigger": "test"}
    
    # Needs actual .wat binary to be present in rules/ which we created in Slice 10.2
    # Ensure it doesn't crash
    try:
        result = registry.run_rule("tls_compliance", ctx)
        assert result is not None
        # From Slice 10.2, we know the placeholder outputs "findings" key
        if "findings" in result:
             assert isinstance(result["findings"], list)
    except Exception as e:
        pytest.fail(f"Execution failed: {e}")

def test_api_endpoint_integration():
    req = RunRuleRequest(
        rule_id="tls_compliance",
        input_context={}
    )
    resp = run_rule_endpoint(req)
    assert resp.rule_id == "tls_compliance"
    assert resp.output is not None
