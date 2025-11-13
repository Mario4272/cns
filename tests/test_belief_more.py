from __future__ import annotations

from datetime import datetime, timezone

from cns_py.cql.belief import compute


def test_belief_none_base_treated_as_zero():
    conf, details = compute(None, None)
    assert details["base_belief"] == 0.0
    assert 0.0 <= conf <= 0.5


def test_belief_monotonic_with_base_belief():
    # With same timestamp, higher base belief should yield higher confidence
    now = datetime.now(timezone.utc)
    conf_low, _ = compute(0.1, now)
    conf_mid, _ = compute(0.5, now)
    conf_high, _ = compute(0.9, now)
    assert conf_low < conf_mid < conf_high
