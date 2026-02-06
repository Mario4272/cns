"""
Regression tests for P13.2 Receipt Stability.
Ensures API/CQL outputs do not drift from the "Golden Master" contract.
"""

import json
import os
from datetime import datetime

import pytest

from cns_py.cql.executor import cql

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden", "receipt_explain_v1.json")
QUERY = 'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2024-12-31T12:00:00Z RETURN EXPLAIN'


def normalize(obj):
    """Recursively strip volatile fields (must match generate_golden.py logic)."""
    if isinstance(obj, dict):
        if "total_ms" in obj:
            obj["total_ms"] = 0.0
        if "ms" in obj:
            obj["ms"] = 0.0
        for k, v in obj.items():
            obj[k] = normalize(v)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = normalize(item)
    return obj


def test_explain_schema_stability():
    """
    Execute the canonical receipt query and verify it matches the Golden Master.
    """
    if not os.path.exists(GOLDEN_PATH):
        pytest.fail(f"Golden master not found at {GOLDEN_PATH}")

    # Execute
    res = cql(QUERY)
    actual = normalize(res)

    # Load Golden
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # JSON round-trip actual to handle datetime serialization matching
    actual_json = json.loads(
        json.dumps(
            actual, default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x)
        )
    )

    # Assert
    # We sort keys in assertion execution or rely on deepdiff if available,
    # but here standard dict equality check works if keys are present.
    # We used sort_keys=True in generation, but dict comparison in Python is insensitive to order.
    # However, list order matters (which is good, we want determinism).

    assert actual_json == expected, (
        "Current output does not match Golden Master. "
        "If change is intentional, run scripts/generate_golden.py."
    )


def test_belief_term_stability():
    """
    Verify specific expected math terms are present in the golden file (sanity check).
    """
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Navigate to belief_compute step
    steps = data.get("explain", {}).get("steps", [])
    belief_step = next((s for s in steps if s["name"] == "belief_compute"), None)
    assert belief_step is not None, "belief_compute step missing from golden file"

    extra = belief_step.get("extra", {})
    assert "belief_terms" in extra, "belief_terms missing from explanation"

    # Check for at least one fiber with expected terms
    terms_map = extra["belief_terms"]
    assert len(terms_map) > 0, "No belief terms recorded in golden file"

    # Pick first
    first_key = list(terms_map.keys())[0]
    terms = terms_map[first_key]["terms"]

    # Ensure our standard factors are tracked
    # Ensure our standard factors are tracked (updated to match current explain implementation)
    expected_factors = {
        "input_belief",
        "contradiction_factor",
        "decay_factor",
        "provenance_boost",
        "config",
        "final_raw",
        "final_clamped",
        "intrinsic_score",
    }
    assert set(terms.keys()).issuperset(
        expected_factors
    ), f"Belief factors drifted. Found: {terms.keys()}"
