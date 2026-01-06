
import pytest
from datetime import datetime, timedelta, timezone
from cns_py.cql.belief import compute_effective_belief as compute, BeliefConfig

def test_belief_defaults():
    # Base belief 1.0, fresh, no bias
    b, _ = compute(1.0, datetime.now(timezone.utc))
    assert 1.0 >= b >= 0.0
    # Should be close to 1.0 if no decay
    # With defaults: decay=1.0, contra=1.0, prov=0.0 -> 1.0
    assert b == 1.0

def test_time_decay():
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=365) # 1 year old
    # Default halflife is 365 days
    # Factor = 0.5
    b, det = compute(1.0, old)
    assert abs(det["decay_factor"] - 0.5) < 0.01
    assert abs(b - 0.5) < 0.01

def test_contradiction_penalty():
    # 1 contradiction, penalty default 0.5
    # Factor = 1.0 - (0.5 * 1) = 0.5
    b, det = compute(1.0, datetime.now(timezone.utc), contradiction_count=1)
    assert abs(det["contradiction_factor"] - 0.5) < 0.01
    assert abs(b - 0.5) < 0.01
    
    # 2 contradictions -> 0.0
    b2, _ = compute(1.0, datetime.now(timezone.utc), contradiction_count=2)
    assert b2 == 0.0

def test_provenance_boost():
    # Base belief 0.5 (uncertain)
    # Add 4 sources (weight 0.1 each) -> +0.4
    # Result 0.9
    b, det = compute(0.5, datetime.now(timezone.utc), provenance_count=4)
    assert abs(det["provenance_boost"] - 0.4) < 0.01
    assert abs(b - 0.9) < 0.01
    
    # Max cap check (default max 0.9)
    # 20 sources -> +2.0 boost? No, capped at 0.9
    b_cap, det_cap = compute(0.0, datetime.now(timezone.utc), provenance_count=20)
    assert det_cap["provenance_boost"] == 0.9
    assert b_cap == 0.9

def test_determinism():
    ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
    res1, _ = compute(0.8, ts, contradiction_count=1, provenance_count=2)
    res2, _ = compute(0.8, ts, contradiction_count=1, provenance_count=2)
    assert res1 == res2
