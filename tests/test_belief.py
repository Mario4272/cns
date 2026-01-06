from datetime import datetime, timezone

from cns_py.cql.belief import BeliefConfig, compute


def test_belief_defaults():
    """Test standard belief computation with defaults."""
    # current_belief 1.0 (very confident), fresh observation
    conf, details = compute(current_belief=1.0, observed_at=datetime.now(timezone.utc))
    assert conf > 0.9
    assert details["input_belief"] == 1.0


def test_belief_decay():
    """Test recency decay reduces confidence."""
    # Old observation (365 days ago)
    now = datetime.now(timezone.utc)
    # Halflife is widely default 365 or similar in logic?
    # Logic: 0.5 ^ (days / halflife)
    # If we assume default halflife, we check relative.

    old_ts = datetime.fromtimestamp(now.timestamp() - 365 * 24 * 3600, tz=timezone.utc)

    conf_fresh, _ = compute(current_belief=1.0, observed_at=now)
    conf_old, _ = compute(current_belief=1.0, observed_at=old_ts)

    # With decay enabled by default
    assert conf_old < conf_fresh


def test_provenance_boost():
    """Test provenance count boosts confidence."""
    cfg = BeliefConfig(base_provenance_weight=0.1, max_provenance_weight=0.5)

    # Base 0.5
    conf_base, _ = compute(current_belief=0.5, observed_at=None, provenance_count=0, cfg=cfg)

    # Boosted
    conf_boosted, _ = compute(current_belief=0.5, observed_at=None, provenance_count=3, cfg=cfg)

    assert conf_boosted > conf_base
    # 0.5 (intrinsic) + 0.3 (boost) = 0.8
    assert abs(conf_boosted - 0.8) < 0.01


def test_contradiction_penalty():
    """Test contradictions heavily penalize confidence."""
    cfg = BeliefConfig(contradiction_penalty=0.5)

    # No contradictions
    conf_clean, _ = compute(current_belief=1.0, observed_at=None, contradiction_count=0, cfg=cfg)

    # 1 Contradiction (penalty 0.5 -> factor 0.5)
    conf_dirty, _ = compute(current_belief=1.0, observed_at=None, contradiction_count=1, cfg=cfg)

    assert conf_dirty < conf_clean
    assert abs(conf_dirty - 0.5) < 0.01

    # 2 Contradictions (penalty 1.0 -> factor 0.0)
    conf_dead, _ = compute(current_belief=1.0, observed_at=None, contradiction_count=2, cfg=cfg)
    assert conf_dead == 0.0
