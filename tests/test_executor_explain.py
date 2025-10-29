from __future__ import annotations

from typing import Dict, List

from cns_py.cql.executor import cql
from cns_py.storage.db import get_conn


def _steps_by_name(explain: Dict) -> Dict[str, Dict]:
    return {s.get("name"): s for s in explain.get("steps", [])}


def test_explain_contains_stage_timings_and_belief_terms():
    # Use demo query that should produce rows and explain
    out = cql(
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE"
    )
    assert "explain" in out
    explain = out["explain"]
    steps = _steps_by_name(explain)
    # Required steps present
    for name in ("ann_shortlist", "temporal_mask", "graph_traverse", "belief_compute"):
        assert name in steps
        assert steps[name].get("ms") is not None
    # Belief compute should report items and belief_terms
    belief_step = steps["belief_compute"]
    extra = belief_step.get("extra", {})
    assert "items" in extra
    assert "belief_terms" in extra and isinstance(extra["belief_terms"], dict)
    # Results must have provenance per contract
    results: List[Dict] = out.get("results", [])
    for r in results:
        prov = r.get("provenance")
        assert isinstance(prov, list) and len(prov) >= 1


def test_citations_contract_drops_rows_without_provenance():
    # Seed a relation without aspects/provenance and verify it doesn't appear in results
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Create atoms
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id",
                ("Entity", "TestProvSubject"),
            )
            subj_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id",
                ("Concept", "TestProvObj"),
            )
            obj_id = cur.fetchone()[0]
            # Link fiber without inserting an aspect row
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s)",
                (subj_id, obj_id, "supports_tls"),
            )
    # Query should return zero rows due to citations contract
    out = cql('MATCH label="TestProvSubject" PREDICATE supports_tls ' "RETURN EXPLAIN PROVENANCE")
    assert "results" in out and len(out["results"]) == 0
