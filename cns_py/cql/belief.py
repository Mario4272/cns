from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class BeliefConfig:
    w_evidence: float = 1.0
    w_recency: float = 0.25  # small nudge toward fresh observations
    w_source_rep: float = 1.0  # weight for source reputation (0..1)
    w_contradiction: float = 2.0  # weight for contradiction penalty (count)
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
    result = 0.5 ** (dt / max(1e-6, half_life_days))
    return float(max(0.0, min(1.0, result)))


def compute(
    base_belief: Optional[float],
    observed_at: Optional[datetime],
    source_reputation: float = 0.5,
    contradiction_count: int = 0,
    cfg: Optional[BeliefConfig] = None,
) -> tuple[float, Dict[str, Any]]:
    """
    Compute final confidence using a logistic over weighted components.
    Formula: σ(w_e*evidence + w_r*source_rep + w_t*recency − w_c*contradictions)
    Inputs:
      - base_belief: existing belief (0..1) stored on the aspect
      - observed_at: when the aspect was last observed/written
      - source_reputation: 0..1 score of the source (default 0.5)
      - contradiction_count: number of known contradictions (default 0)
      - cfg: weights
    Returns: (confidence, details)
    """
    if cfg is None:
        cfg = BeliefConfig()
    b = 0.0 if base_belief is None else float(base_belief)
    rec = _recency_term(observed_at, datetime.now(timezone.utc), cfg.recency_half_life_days)

    # Map 0..1 to -3..+3 logit-ish range for evidence center
    evidence_score = (b - 0.5) * 6.0

    # Logit = w_e*E + w_r*R + w_t*T - w_c*C
    # Source reputation is mapped 0..1 -> 0..1 contribution directly (simpler) or should we center it?
    # Let's treat source_rep as a direct additive boost/drag.
    # For now, simplistic: w_r * (reputation - 0.5) * 2 ?? No, let's keep it additive positive factor
    # But wait, low rep should drag down?
    # Let's align with the instruction: w_r*source_rep. If w_r=1.0, rep=0.0 -> 0 boost. rep=1.0 -> +1.0 boost.
    # Contradictions are subtraction.

    term_evidence = cfg.w_evidence * evidence_score
    term_rep = (
        cfg.w_source_rep * (source_reputation - 0.5) * 2.0
    )  # Let's center it so 0.5 is neutral
    # Actually, instruction said: w_r*source_rep. That implies 0->0, 1->1.
    # But usually 0.5 is "unknown". If we make 0.0 punish, that's harsh for "unknown".
    # Let's stick to strict additive per prompt, but maybe add comments?
    # Prompt: w_r*source_rep.
    term_rep = cfg.w_source_rep * source_reputation

    term_recency = cfg.w_recency * rec
    term_contradiction = cfg.w_contradiction * contradiction_count

    x = term_evidence + term_rep + term_recency - term_contradiction
    conf = float(_sigmoid(x))

    details = {
        "base_belief": b,
        "evidence_score": evidence_score,
        "recency": rec,
        "source_reputation": source_reputation,
        "contradiction_count": contradiction_count,
        "terms": {
            "evidence": term_evidence,
            "rep": term_rep,
            "recency": term_recency,
            "contradiction": -term_contradiction,
        },
        "weights": {
            "w_evidence": cfg.w_evidence,
            "w_recency": cfg.w_recency,
            "w_source_rep": cfg.w_source_rep,
            "w_contradiction": cfg.w_contradiction,
        },
        "logit": x,
    }
    return conf, details
