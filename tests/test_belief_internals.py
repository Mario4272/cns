from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cns_py.cql.belief import _recency_term, _sigmoid


def test_sigmoid_extremes_and_bounds():
    assert _sigmoid(1000.0) == 1.0
    assert _sigmoid(-1000.0) == 0.0
    mid = _sigmoid(0.0)
    assert 0.49 <= mid <= 0.51


essentially_zero = 1e-6


def test_recency_term_none_and_half_life_behavior():
    # None observed_at yields 0.0
    assert _recency_term(None, None, 365.0) == 0.0

    now = datetime.now(timezone.utc)
    # At t=0 days, recency should be ~1.0
    r0 = _recency_term(now, now, 10.0)
    assert 0.99 <= r0 <= 1.0

    # At half-life days, recency ~0.5
    r_half = _recency_term(now - timedelta(days=10.0), now, 10.0)
    assert 0.45 <= r_half <= 0.55

    # Very large delta drives toward 0.0 (but clamped ≥0)
    r_old = _recency_term(now - timedelta(days=10000), now, 10.0)
    assert 0.0 <= r_old <= 0.01
