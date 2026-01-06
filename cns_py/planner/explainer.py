"""
Planner Explainability (Slice 11.1).
Provides logic to generate deterministic hash and audit wrapper for plans.
"""
from typing import Dict, Any, Optional
import hashlib
from cns_py.crypto.canonical import canonicalize
from cns_py.planner.plan import RetrievalPlan
from cns_py.planner.planner import Planner
from pydantic import BaseModel

class PlanExplanation(BaseModel):
    query: str
    plan_hash: str
    plan: Dict[str, Any]
    rationale: Any
    determinism: bool = True

class PlanExplainer:
    def __init__(self, planner: Optional[Planner] = None):
        self.planner = planner or Planner()

    def explain(self, query: str, **kwargs) -> PlanExplanation:
        """
        Generates a plan and wraps it with explainability metadata (hash, rationale).
        """
        # Generate plan
        plan = self.planner.plan(query)
        
        # Canonicalize Plan for Hashing
        # We strip dynamic fields if any (timestamp?). Currently Plan is deterministic.
        plan_dict = plan.dict()
        
        # Create hash
        canon_bytes = canonicalize(plan_dict)
        plan_hash = hashlib.sha256(canon_bytes).hexdigest()
        
        return PlanExplanation(
            query=query,
            plan_hash=plan_hash,
            plan=plan_dict,
            rationale=plan.rationale
        )
