from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cns_py.cql.belief import BeliefConfig, compute


def test_belief_compute_baseline_only():
    # With base belief = 0.5 and default weights, evidence_score = 0; confidence near 0.5
    conf, details = compute(0.5, None)
    assert 0.45 <= conf <= 0.55
    assert details["base_belief"] == 0.5


def test_belief_recency_recent_higher_than_old():
    now = datetime.now(timezone.utc)
    cfg = BeliefConfig()
    # Center evidence at 0.5 so recency term drives the difference
    conf_recent, d_recent = compute(0.5, now, cfg)
    conf_old, d_old = compute(0.5, now - timedelta(days=3650), cfg)
    assert d_recent["recency"] > d_old["recency"]
    assert conf_recent > conf_old
