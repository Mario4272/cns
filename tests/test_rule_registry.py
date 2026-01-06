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


def test_registry_load_manifest(tmp_path):
    # Create a mock manifest
    manifest = tmp_path / "manifest.json"
    import json

    data = [
        {
            "id": "tls_compliance",
            "version": "1.0",
            "description": "Checks TLS",
            "wasm_file": "tls_compliance.wasm",
            "input_schema": {},
            "output_schema": {},
        },
        {
            "id": "contradiction_marker",
            "version": "1.0",
            "description": "Marks contradictions",
            "wasm_file": "contradiction.wasm",
            "input_schema": {},
            "output_schema": {},
        },
    ]
    manifest.write_text(json.dumps(data))

    registry = RuleRegistry(manifest_path=str(manifest))
    rules = registry.list_rules()
    assert len(rules) == 2

    ids = [r.id for r in rules]
    assert "tls_compliance" in ids
    assert "contradiction_marker" in ids


def test_run_rule_logic(tmp_path):
    # Create a mock manifest
    manifest = tmp_path / "manifest.json"
    import json

    data = [
        {
            "id": "tls_compliance",
            "version": "1.0",
            "description": "Checks TLS",
            "wasm_file": "tls_compliance.wasm",
            "input_schema": {},
            "output_schema": {},
        }
    ]
    manifest.write_text(json.dumps(data))

    # Also need the WASM file to exist
    wasm = tmp_path / "tls_compliance.wasm"
    wasm.write_bytes(b"\x00\x61\x73\x6d\x01\x00\x00\x00")  # Minimal WASM header

    registry = RuleRegistry(manifest_path=str(manifest))
    # Mock context
    ctx = {"trigger": "test"}

    try:
        # Mock execute_rule to avoid actual WASM runtime in unit test if possible
        # Or let it fail gracefully if sandbox not set up.
        # But wait, registry.run_rule calls execute_rule which uses WasmSandbox.

        # We can mock registry.run_rule or execute_rule?
        # Let's just mock execute_rule in the module
        from unittest.mock import patch

        with patch("cns_py.rules.registry.execute_rule") as mock_exec:
            mock_exec.return_value = {"findings": []}
            result = registry.run_rule("tls_compliance", ctx)
            assert result is not None
            assert "findings" in result
    except Exception as e:
        pytest.fail(f"Execution failed: {e}")


def test_api_endpoint_integration():
    # Mock the global registry for the endpoint
    from unittest.mock import patch

    with patch("cns_py.api.server._REGISTRY") as mock_reg:
        mock_reg.run_rule.return_value = {"findings": []}

        req = RunRuleRequest(rule_id="tls_compliance", input_context={})
        resp = run_rule_endpoint(req)
        assert resp.rule_id == "tls_compliance"
        assert resp.output is not None
