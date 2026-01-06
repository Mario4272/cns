"""
Tests for WASM Rules (Slice 10.2).
Verifies that rule packs execute in the sandbox and return valid Findings.
Uses WAT (text) format since Rust WASM toolchain is unavailable.
"""
import pytest
import os
import json
from cns_py.wasm import execute_rule

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules")

def load_rule(name: str) -> bytes:
    path = os.path.join(RULES_DIR, f"{name}.wat")
    with open(path, "rb") as f:
        return f.read()

def test_tls_compliance_rule():
    """Verify tls_compliance rule returns expected violation."""
    rule_bytes = load_rule("tls_compliance")
    
    # Input is ignored by the placeholder WAT, but we pass valid structure anyway
    input_data = {
        "subject_ids": ["test_subj"],
        "facts": [{"predicate": "uses_algo", "object": "tls1.0"}]
    }
    
    output = execute_rule(rule_bytes, input_data)
    
    assert "findings" in output
    findings = output["findings"]
    assert len(findings) == 1
    assert findings[0]["kind"] == "compliance_violation"
    assert "Weak crypto" in findings[0]["message"]

def test_contradiction_marker_rule():
    """Verify contradiction_marker rule returns expected marking."""
    rule_bytes = load_rule("contradiction_marker")
    
    input_data = {
        "subject_ids": ["test_subj"],
        "context": {"contradictions_count": 1}
    }
    
    output = execute_rule(rule_bytes, input_data)
    
    assert "findings" in output
    findings = output["findings"]
    assert len(findings) == 1
    assert findings[0]["kind"] == "contradiction"
    assert "Contradiction detected" in findings[0]["message"]
