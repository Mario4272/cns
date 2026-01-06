"""
Retrieval Plan Structures (Slice 10.1).
Defines the executable steps and plan container.
"""
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field

# --- Steps ---

class RetrievalStep(BaseModel):
    step_type: str
    description: Optional[str] = None

class ExactQueryStep(RetrievalStep):
    step_type: Literal["exact"] = "exact"
    atom_id: str
    
class VectorSearchStep(RetrievalStep):
    step_type: Literal["vector"] = "vector"
    vector: Optional[List[float]] = None
    query_text: Optional[str] = None # For routing/embedding
    space: str = "default"
    k: int = 10
    filter: Optional[Dict[str, Any]] = None

class WasmRuleStep(RetrievalStep):
    step_type: Literal["wasm_rule"] = "wasm_rule"
    rule_name: str # e.g. "tls_compliance"
    input_context: Dict[str, Any] = Field(default_factory=dict)

# --- Plan ---

class PlanConstraints(BaseModel):
    latency_budget_ms: int = 250
    asof_ts: Optional[str] = None
    require_provenance: bool = True

class RetrievalPlan(BaseModel):
    query_raw: str
    steps: List[Union[ExactQueryStep, VectorSearchStep, WasmRuleStep]]
    constraints: PlanConstraints = Field(default_factory=PlanConstraints)
    rationale: List[Dict[str, str]] = Field(default_factory=list) # List of {"rule": ..., "because": ...}
