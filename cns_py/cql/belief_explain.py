"""
Belief Explainer Module.
Wraps the core belief computation to provide human-readable traces of how a score was derived.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from cns_py.cql.belief import compute_effective_belief, BeliefConfig

class ExplanationStep(BaseModel):
    name: str           # e.g. "Time Decay"
    impact: str         # e.g. "x0.5" or "-0.2"
    description: str    # e.g. "Observed 365 days ago (1.0 halflives)"
    value_after: float  # Score after this step

class BeliefExplanation(BaseModel):
    final_score: float
    steps: List[ExplanationStep]
    input_summary: str  # e.g. "Base 1.0, 1 yr old, 2 contradictions"

class BeliefExplainer:
    def __init__(self, config: Optional[BeliefConfig] = None):
        self.config = config or BeliefConfig()

    def explain(
        self,
        base_belief: float,
        observed_at: Optional[datetime],
        provenance_count: int,
        contradiction_count: int,
    ) -> BeliefExplanation:
        """
        Run computation and generate a step-by-step trace.
        """
        # Run core logic
        score, details = compute_effective_belief(
            base_belief, observed_at, provenance_count, contradiction_count, self.config
        )
        
        # Unpack details for the story
        decay = details["decay_factor"]
        contra_factor = details["contradiction_factor"]
        prov_boost = details["provenance_boost"]
        intrinsic = details["intrinsic_score"]
        
        steps = []
        
        # Step 1: Base
        steps.append(ExplanationStep(
            name="Base Belief",
            impact=f"{base_belief:.2f}",
            description="Initial confidence from source extraction.",
            value_after=base_belief
        ))
        
        # Step 2: Decay
        if observed_at and self.config.decay_enabled:
            # Calc age for description
            now = datetime.now(timezone.utc)
            days_old = (now - observed_at).total_seconds() / 86400.0
            steps.append(ExplanationStep(
                name="Time Decay",
                impact=f"x{decay:.2f}",
                description=f"Observed {days_old:.1f} days ago (Halflife {self.config.decay_halflife_days}d)",
                value_after=base_belief * decay
            ))
            
        # Step 3: Contradictions
        # current running value
        running_val = base_belief * decay
        if contradiction_count > 0:
            steps.append(ExplanationStep(
                name="Contradictions",
                impact=f"x{contra_factor:.2f}",
                description=f"{contradiction_count} contradictions found (Penalty {self.config.contradiction_penalty} each)",
                value_after=intrinsic
            ))
        else:
             steps.append(ExplanationStep(
                name="Contradictions",
                impact="None",
                description="No contradictions found.",
                value_after=intrinsic
            ))
            
        # Step 4: Provenance
        if provenance_count > 0:
             steps.append(ExplanationStep(
                name="Provenance Boost",
                impact=f"+{prov_boost:.2f}",
                description=f"Supported by {provenance_count} citations (Weight {self.config.base_provenance_weight})",
                value_after=details["final_raw"] # Might be unclamped
            ))
            
        # Step 5: Clamping
        if details["final_raw"] > 1.0 or details["final_raw"] < 0.0:
             steps.append(ExplanationStep(
                name="Clamping",
                impact="",
                description="Score restricted to [0.0, 1.0] range.",
                value_after=score
            ))
            
        return BeliefExplanation(
            final_score=score,
            steps=steps,
            input_summary=f"Base={base_belief}, Prov={provenance_count}, Contra={contradiction_count}"
        )
