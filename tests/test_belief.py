from datetime import datetime, timezone

from cns_py.cql.belief import BeliefConfig, compute


def test_belief_defaults():
    """Test standard belief computation with defaults."""
    # Base belief 1.0 (very confident), fresh observation
    conf, details = compute(base_belief=1.0, observed_at=datetime.now(timezone.utc))
    assert conf > 0.9
    assert details["base_belief"] == 1.0


def test_belief_decay():
    """Test recency decay reduces confidence."""
    # Old observation (365 days ago)
    now = datetime.now(timezone.utc)
    old_ts = datetime.fromtimestamp(now.timestamp() - 365 * 24 * 3600, tz=timezone.utc)

    conf_fresh, _ = compute(base_belief=1.0, observed_at=now)
    conf_old, _ = compute(base_belief=1.0, observed_at=old_ts)

    assert conf_old < conf_fresh


def test_source_reputation():
    """Test source reputation boosts confidence."""
    # Low reputation vs High reputation
    # Note: Using small base belief to see the lift clearly

    cfg = BeliefConfig(w_source_rep=2.0)

    # Low rep (0.1)
    conf_low, _ = compute(base_belief=0.5, observed_at=None, source_reputation=0.1, cfg=cfg)

    # High rep (0.9)
    conf_high, _ = compute(base_belief=0.5, observed_at=None, source_reputation=0.9, cfg=cfg)

    assert conf_high > conf_low


def test_contradiction_penalty():
    """Test contradictions heavily penalize confidence."""
    cfg = BeliefConfig(w_contradiction=3.0)

    # No contradictions
    conf_clean, _ = compute(base_belief=0.9, observed_at=None, contradiction_count=0, cfg=cfg)

    # 1 Contradiction
    conf_dirty, _ = compute(base_belief=0.9, observed_at=None, contradiction_count=1, cfg=cfg)

    assert conf_dirty < conf_clean
    assert conf_dirty < 0.5  # Should likely tank it below 50% given the weight


def test_formula_integration():
    """Verify all terms interact: σ(w_e*E + w_r*R + w_t*T - w_c*C)"""
    # High evidence (1.0), High Rep (1.0), Fresh (1.0), BUT 2 Contradictions
    # Should result in low confidence

    cfg = BeliefConfig(w_evidence=1.0, w_source_rep=1.0, w_recency=0.25, w_contradiction=2.0)

    # Evidence score for 1.0 -> (1.0 - 0.5)*6 = 3.0
    # Source Rep 1.0 -> 1.0
    # Recency 1.0 -> 0.25
    # Contradictions 2 -> -2.0 * 2 = -4.0
    # Logit = 3.0 + 1.0 + 0.25 - 4.0 = 0.25
    # Sigmoid(0.25) ~ 0.56

    conf, details = compute(
        base_belief=1.0,
        observed_at=datetime.now(timezone.utc),
        source_reputation=1.0,
        contradiction_count=2,
        cfg=cfg,
    )

    assert 0.5 < conf < 0.6
    assert details["logit"] == 0.25


def test_belief_null_handling():
    """Test NULL inputs produce deterministic outputs."""
    # Null base_belief -> 0.0
    conf_null_belief, _ = compute(base_belief=None, observed_at=None)
    conf_zero_belief, _ = compute(base_belief=0.0, observed_at=None)
    assert conf_null_belief == conf_zero_belief

    # Null observed_at -> recency=0.0
    conf_null_time, details = compute(base_belief=0.5, observed_at=None)
    assert details["recency"] == 0.0
