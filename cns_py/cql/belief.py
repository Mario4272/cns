from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from cns_py.cql.belief_config import BeliefConfig


def _sigmoid(x: float) -> float:
    try:
        if x > 50:
            return 1.0
        if x < -50:
            return 0.0
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _recency_modifier(
    observed_at: Optional[datetime], now: Optional[datetime], halflife_days: float
) -> float:
    """
    Returns a multiplier (0..1) based on age.
    1.0 means just observed. Decays exponentially.
    """
    if not observed_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    # Ensure non-negative age
    age_seconds = max(0.0, (now - observed_at).total_seconds())
    days = age_seconds / (86400.0)

    # Formula: 0.5 ^ (days / halflife)
    # If days=halflife, factor=0.5
    factor = 0.5 ** (days / max(1e-6, halflife_days))
    return float(max(0.0, min(1.0, factor)))


def compute_effective_belief(
    current_belief: float | None,
    observed_at: Optional[datetime],
    provenance_count: int = 0,
    contradiction_count: int = 0,
    # Future: Signed provenance strength could be passed here
    cfg: Optional[BeliefConfig] = None,
) -> tuple[float, Dict[str, Any]]:
    """
    Phase 12 Belief Update Rule.

    Logic:
    1. Start with current_belief (default 1.0 if new).
    2. Apply Time Decay (multiplicative).
    3. Apply Contradiction Penalty (multiplicative reduction).
    4. Apply Provenance Boost (additive sigmoid term?).
       Actually, `val_replies` says: "Time decay... Contradiction penalty... Provenance weighting".

    Let's stick to a robust component model:

    Projected Belief = Base * Decay * (1 - Penalty * Contradictions) + (ProvenanceBoost)

    However, 0..1 bounding is key.

    Revised Formula for V1:
    - Base = current_belief
    - Decay = _recency_modifier(...)
    - ContradictionFactor = max(0.0, 1.0 - (cfg.contradiction_penalty * count))
    - ProvenanceBoost = min(cfg.max_provenance_weight, count * cfg.base_provenance_weight)

    Final = (Base * Decay * ContradictionFactor) + ProvenanceBoost
    Clamped to [0.0, 1.0].

    Args:
        current_belief: The raw confidence recorded (usually 1.0 for a fact).
        observed_at: Timestamp of observation.
        provenance_count: Number of supporting citations/signatures.
        contradiction_count: Number of contradictory claims.
        cfg: Configuration object.

    Returns:
        (final_score, details_dict)
    """
    if cfg is None:
        cfg = BeliefConfig()

    # 1. Decay
    decay_factor = 1.0
    if cfg.decay_enabled and observed_at:
        decay_factor = _recency_modifier(observed_at, None, cfg.decay_halflife_days)

    # 2. Contradiction
    # e.g. if penalty=0.5, 1 contradiction halves the belief. 2 zeroes it.
    penalty_raw = cfg.contradiction_penalty * contradiction_count
    contradiction_factor = max(0.0, 1.0 - penalty_raw)

    # 3. Provenance
    # e.g. 0.1 * 3 sources = +0.3 boost
    prov_boost = min(cfg.max_provenance_weight, provenance_count * cfg.base_provenance_weight)

    # 4. Combine
    # We apply decay and contradiction to the "intrinsic" belief
    current_val = current_belief if current_belief is not None else 0.0
    intrinsic = current_val * decay_factor * contradiction_factor

    # Then add provenance support (external evidence)
    # This mirrors "I remember X (decayed/disputed) BUT I see Y sources confirming it."
    # We clamp the result.
    raw_final = intrinsic + prov_boost
    final_score = float(max(0.0, min(1.0, raw_final)))

    details = {
        "input_belief": current_val,
        "decay_factor": decay_factor,
        "contradiction_factor": contradiction_factor,
        "provenance_boost": prov_boost,
        "intrinsic_score": intrinsic,
        "final_raw": raw_final,
        "final_clamped": final_score,
        "config": {
            "halflife": cfg.decay_halflife_days,
            "penalty_per_contradiction": cfg.contradiction_penalty,
            "weight_per_proof": cfg.base_provenance_weight,
        },
    }

    return final_score, details


# Alias for backward compatibility if needed, though we should migrate calls
compute = compute_effective_belief

__all__ = ["compute_effective_belief", "compute", "BeliefConfig", "_recency_modifier", "_sigmoid"]
