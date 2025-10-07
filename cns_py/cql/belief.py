from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class BeliefConfig:
    w_evidence: float = 1.0
    w_recency: float = 0.25  # small nudge toward fresh observations
    recency_half_life_days: float = 365.0  # half-life for recency contribution


def _sigmoid(x: float) -> float:
    try:
        if x > 50:
            return 1.0
        if x < -50:
            return 0.0
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _recency_term(
    observed_at: Optional[datetime], now: Optional[datetime], half_life_days: float
) -> float:
    if not observed_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    dt = abs((now - observed_at).total_seconds()) / (60 * 60 * 24)
    # Exponential decay: 1.0 at t=0; 0.5 at t=half_life
    return max(0.0, min(1.0, 0.5 ** (dt / max(1e-6, half_life_days))))


def compute(
    base_belief: Optional[float],
    observed_at: Optional[datetime],
    cfg: Optional[BeliefConfig] = None,
) -> tuple[float, Dict[str, Any]]:
    """
    Compute final confidence using a logistic over weighted components.
    Inputs:
      - base_belief: existing belief (0..1) stored on the aspect
      - observed_at: when the aspect was last observed/written
      - cfg: weights
    Returns: (confidence, details)
    """
    if cfg is None:
        cfg = BeliefConfig()
    b = 0.0 if base_belief is None else float(base_belief)
    rec = _recency_term(observed_at, datetime.now(timezone.utc), cfg.recency_half_life_days)

    # Map 0..1 to -3..+3 logit-ish range for evidence center, then add recency nudge
    evidence_score = (b - 0.5) * 6.0
    x = cfg.w_evidence * evidence_score + cfg.w_recency * rec
    conf = float(_sigmoid(x))

    details = {
        "base_belief": b,
        "evidence_score": evidence_score,
        "recency": rec,
        "weights": {
            "w_evidence": cfg.w_evidence,
            "w_recency": cfg.w_recency,
        },
        "logit": x,
    }
    return conf, details
