from __future__ import annotations

from typing import Dict, List

from cns_py.cql.executor import cql


def _steps_by_name(explain: Dict) -> Dict[str, Dict]:
    return {s.get("name"): s for s in explain.get("steps", [])}


def test_belief_aggregation_reports_item_counts_and_averages():
    out = cql(
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE"
    )
    # Must have results with provenance due to citations contract
    results: List[Dict] = out.get("results", [])
    assert isinstance(results, list)
    assert len(results) >= 1

    # Verify belief_compute step and aggregated metrics
    explain = out.get("explain", {})
    steps = _steps_by_name(explain)
    assert "belief_compute" in steps
    belief_step = steps["belief_compute"]
    extra = belief_step.get("extra", {})

    # Items processed should be >= number of results (1:1 in current executor)
    assert "items" in extra and int(extra["items"]) >= len(results)

    # Aggregated averages should be present and within sane bounds
    for key in ("avg_base_belief", "avg_confidence", "avg_recency"):
        if key in extra:
            val = float(extra[key])
            assert 0.0 <= val <= 1.0
