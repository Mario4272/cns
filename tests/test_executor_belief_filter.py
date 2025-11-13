from __future__ import annotations

from typing import Dict

from cns_py.cql.executor import cql


def _steps_by_name(explain: Dict) -> Dict[str, Dict]:
    return {s.get("name"): s for s in explain.get("steps", [])}


def test_belief_ge_filter_drops_low_confidence_rows():
    # High threshold should filter out most rows, possibly all
    out = cql(
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z BELIEF >= 0.99 RETURN EXPLAIN PROVENANCE"
    )
    assert "results" in out
    # Either empty or very few results at such a high cutoff
    assert len(out["results"]) <= 1
    # If results exist, ensure they meet the cutoff
    for r in out["results"]:
        assert float(r.get("confidence", 0.0)) >= 0.99
