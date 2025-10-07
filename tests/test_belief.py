from datetime import datetime, timedelta, timezone

from cns_py.cql.belief import BeliefConfig, compute


def test_belief_sigmoid_monotonic():
    c_low, _ = compute(0.2, datetime.now(timezone.utc) - timedelta(days=365))
    c_mid, _ = compute(0.5, datetime.now(timezone.utc))
    c_high, _ = compute(0.9, datetime.now(timezone.utc))
    assert c_low < c_mid < c_high


def test_belief_recency_effect():
    now = datetime.now(timezone.utc)
    cfg = BeliefConfig(w_evidence=0.0, w_recency=1.0, recency_half_life_days=30)
    c_fresh, _ = compute(0.5, now, cfg)
    c_old, _ = compute(0.5, now - timedelta(days=365), cfg)
    assert c_fresh > c_old
