from __future__ import annotations

from datetime import datetime
from typing import Dict

from cns_py.cql.executor import _asof_bounds, cql


def _steps_by_name(explain: Dict) -> Dict[str, Dict]:
    return {s.get("name"): s for s in explain.get("steps", [])}


def test_asof_bounds_none_and_iso_roundtrip():
    start, end = _asof_bounds(None)
    assert start is None and end is None

    iso = "2025-01-01T00:00:00Z"
    start2, end2 = _asof_bounds(iso)
    assert isinstance(start2, datetime) and isinstance(end2, datetime)
    assert start2 == end2
    assert start2.tzinfo is not None


def test_explain_total_and_step_timings_are_non_negative():
    out = cql(
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE"
    )
    assert "explain" in out
    explain = out["explain"]
    assert "total_ms" in explain
    total_ms = float(explain["total_ms"])  # ensure castable to float
    assert total_ms >= 0.0

    steps = _steps_by_name(explain)
    # Validate all known steps report non-negative timing
    for name in ("planner", "ann_shortlist", "temporal_mask", "graph_traverse", "belief_compute"):
        assert name in steps
        ms = float(steps[name].get("ms", -1))
        assert ms >= 0.0
