from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Minimal CQL planner skeleton for Phase 1/2


@dataclass
class Match:
    label: Optional[str] = None  # e.g., entity label
    predicate: Optional[str] = None  # e.g., 'supports_tls'


@dataclass
class Similar:
    to_label: str
    k: int = 5


@dataclass
class Belief:
    ge: Optional[float] = None


@dataclass
class AsOf:
    timestamp_iso: str  # ISO8601 string


@dataclass
class Plan:
    match: Optional[Match] = None
    similar: Optional[Similar] = None
    belief: Optional[Belief] = None
    asof: Optional[AsOf] = None


def explain(plan: Plan) -> str:
    steps = []
    if plan.similar:
        steps.append(f"ANN shortlist around '{plan.similar.to_label}' (k={plan.similar.k})")
    if plan.asof:
        steps.append(f"Temporal mask at {plan.asof.timestamp_iso}")
    if plan.match:
        if plan.match.predicate:
            steps.append(f"Graph expand via predicate '{plan.match.predicate}'")
        if plan.match.label:
            steps.append(f"Filter by label == '{plan.match.label}'")
    if plan.belief and plan.belief.ge is not None:
        steps.append(f"Belief >= {plan.belief.ge}")
    if not steps:
        return "No-op plan"
    return " -> ".join(steps)
