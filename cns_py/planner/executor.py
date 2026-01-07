"""
Plan Executor (Slice 10.1).
Executes RetrievalSteps and aggregates Findings.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from cns_py.planner.plan import ExactQueryStep, RetrievalPlan, VectorSearchStep, WasmRuleStep
from cns_py.vector.manager import IndexManager

# If we had a global instance or dependency injection, we'd use it.
# For now, let's assume we can import the singleton or instantiate.
# The server uses a global _INDEX_MANAGER. We might need similar access.
# Ideally, Executor is passed the context/managers.

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    step_index: int
    step_type: str
    items: List[Any] = []  # Atoms or Vector Results
    rule_output: Optional[Dict[str, Any]] = None


class Findings(BaseModel):
    plan_id: Optional[str] = None
    results: List[RetrievalResult] = []


class Executor:
    def __init__(self, vector_manager: IndexManager):
        self.vector_manager = vector_manager

    def execute(self, plan: RetrievalPlan) -> Findings:
        findings = Findings()

        for i, step in enumerate(plan.steps):
            result = RetrievalResult(step_index=i, step_type=step.step_type)

            try:
                if isinstance(step, ExactQueryStep):
                    # TODO: Implement DB lookup. For v0, stub or use a mock lookup.
                    # In real code: with get_conn()... SELECT * FROM atoms WHERE id = step.atom_id
                    logger.info(f"Executing Exact Query for {step.atom_id}")
                    # Stub result
                    result.items = [{"id": step.atom_id, "mock_content": "Found it"}]

                elif isinstance(step, VectorSearchStep):
                    logger.info(f"Executing Vector Search in {step.space} for '{step.query_text}'")
                    # Use manager
                    # Note: manager needs to be started/ready
                    if step.vector:
                        vec = step.vector
                    else:
                        # If no vector, manager.query(space='auto'/'specific', text=...) handles
                        # embedding?
                        # Wait, manager.query logic added in P9.2 handles text->one_vec embedding
                        # inside find_similar API, but manager.query itself expects a vector.
                        # We might need to embed here or rely on manager refactor.
                        # Let's check manager.query again. It takes query_vec.
                        # So Executor needs access to Embedder to turn text->vec.
                        txt = step.query_text or ""
                        vec = self.vector_manager.provider.embed_texts([txt])[0]

                    hits = self.vector_manager.query(
                        query_vec=vec,
                        k=step.k,
                        space=step.space,
                        query_text=step.query_text,
                        # Use text for auto-routing refined check if needed
                    )
                    result.items = hits

                elif isinstance(step, WasmRuleStep):
                    logger.info(f"Executing WASM Rule {step.rule_name}")
                    # Load rule binary
                    import os

                    from cns_py.wasm import execute_rule

                    # Assume rules are in "rules/" at repo root or relative known path
                    # For demo/dev, let's find repo root relative to this file
                    # cns_py/planner/executor.py -> .../cns
                    repo_root = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    rule_path = os.path.join(repo_root, "rules", f"{step.rule_name}.wat")

                    if not os.path.exists(rule_path):
                        # Fallback for .wasm if implemented later
                        rule_path = os.path.join(repo_root, "rules", f"{step.rule_name}.wasm")

                    if not os.path.exists(rule_path):
                        result.rule_output = {"error": f"Rule binary not found: {step.rule_name}"}
                    else:
                        with open(rule_path, "rb") as f:
                            rule_bytes = f.read()

                        # Execute
                        # Context: Pass what we have. findings so far?
                        # For now, just pass the step.input_context + mock data to satisfy rule
                        # contract
                        input_data = step.input_context.copy()
                        # Helper: Add mock facts if missing so rules don't crash
                        if "facts" not in input_data:
                            # Trigger violation for demo
                            input_data["facts"] = [{"predicate": "uses_algo", "object": "tls1.0"}]
                        if "subject_ids" not in input_data:
                            input_data["subject_ids"] = ["demo_subject"]

                        output = execute_rule(rule_bytes, input_data)
                        result.rule_output = output

            except Exception as e:
                logger.error(f"Step {i} failed: {e}")
                result.rule_output = {"error": str(e)}

            findings.results.append(result)

        return findings
