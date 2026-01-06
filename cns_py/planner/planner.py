"""
Heuristic Planner (Slice 10.1).
Generates RetrievalPlan from raw query.
"""
from typing import List, Tuple
from cns_py.planner.plan import (
    RetrievalPlan, 
    PlanConstraints,
    ExactQueryStep, 
    VectorSearchStep, 
    WasmRuleStep
)
from cns_py.vector.router import HeuristicRouter

class Planner:
    def __init__(self):
        self.router = HeuristicRouter()

    def plan(self, query: str, constraints: PlanConstraints = None) -> RetrievalPlan:
        if constraints is None:
            constraints = PlanConstraints()
            
        steps = []
        
        rationale = []
        
        # 1. Exact Match Heuristic (Simple ID check)
        # In real system, we might regex for SHA256 or UUID
        if query.startswith("id:") or query.startswith("sha256:"):
            # "id:123" -> ExactQueryStep(atom_id="123")
            atom_id = query.split(":", 1)[1]
            steps.append(ExactQueryStep(atom_id=atom_id, description=f"Fetch atom {atom_id}"))
            rationale.append({"rule": "ExactMatchHeuristic", "because": "Query starts with known ID prefix"})
            
        # 2. Vector Search (Default for everyone unless purely ID)
        # Even if we have an ID, we might want related context.
        # Use Router to pick space
        routes = self.router.route(query) 
        # routes is [(space, weight), ...]
        
        # Sort by weight desc
        routes.sort(key=lambda x: x[1], reverse=True)
        
        # Create a step for the top space (or multiple?)
        # For v0, let's just make one Vector Step per high-confidence space (>0.5)
        # or just the top one if ambiguous.
        top_space, top_weight = routes[0]
        
        steps.append(VectorSearchStep(
            query_text=query,
            space=top_space,
            k=10, 
            description=f"Vector search in '{top_space}' (conf={top_weight})"
        ))
        rationale.append({"rule": "VectorRouter", "because": f"Router selected '{top_space}' with weight {top_weight}"})
        
        # 3. Rule Heuristic
        # If query implies compliance check
        if "compliance" in query.lower() or "policy" in query.lower():
            # Add a rule step.
            # In a real system, we'd pick the specific rule based on more analysis.
            # Here hardcode 'tls_compliance' for the demo.
            steps.append(WasmRuleStep(
                rule_name="tls_compliance",
                input_context={"trigger": "query_keyword"},
                description="Run TLS compliance check"
            ))
            rationale.append({"rule": "ComplianceHeuristic", "because": "Detected compliance keyword"})
            
        return RetrievalPlan(
            query_raw=query,
            steps=steps,
            constraints=constraints,
            rationale=rationale
        )
