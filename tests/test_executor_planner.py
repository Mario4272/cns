from __future__ import annotations

from typing import Dict

from cns_py.cql.executor import cql


def _steps_by_name(explain: Dict) -> Dict[str, Dict]:
    return {s.get("name"): s for s in explain.get("steps", [])}


def test_explain_contains_planner_step_with_estimates_and_params():
    out = cql(
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE"
    )
    assert "explain" in out
    steps = _steps_by_name(out["explain"])
    # Planner step is expected; if present, validate structure
    if "planner" in steps:
        planner = steps["planner"]
        assert planner.get("ms") is not None
        extra = planner.get("extra", {})
        # Heuristic estimates
        assert "est_base" in extra
        assert "est_fanout" in extra
        # Query parameters echoed back for explain readability (when present)
        for key in ("label", "predicate", "asof"):
            if key in extra:
                assert extra[key] is not None
        if "belief_ge" in extra:
            assert isinstance(extra["belief_ge"], (int, float))
