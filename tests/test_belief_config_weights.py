from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cns_py.cql.belief import BeliefConfig, compute


def test_belief_config_higher_recency_weight_increases_influence():
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=365)

    cfg_low = BeliefConfig(w_evidence=1.0, w_recency=0.1)
    cfg_high = BeliefConfig(w_evidence=1.0, w_recency=1.0)

    conf_low, d_low = compute(0.5, old, cfg_low)
    conf_high, d_high = compute(0.5, old, cfg_high)

    assert d_low["recency"] == d_high["recency"]
    assert conf_high > conf_low


def test_belief_config_zero_evidence_weight_relies_on_recency():
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=365)

    cfg = BeliefConfig(w_evidence=0.0, w_recency=1.0)
    conf_now, _ = compute(0.1, now, cfg)
    conf_old, _ = compute(0.9, old, cfg)

    # With zero evidence weight, the more recent observation should win
    assert conf_now > conf_old
