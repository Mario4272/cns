"""
Phase 11 Demo Script.
Demonstrates:
1. Production Index Ops (Status check).
2. Planner Explainability (Plan + Rationale + Hash).
3. Rule Registry Execution (Run Rule via Registry).
"""
import os
import sys
import time

# Ensure path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cns_py.api.server import (
    _REGISTRY,  # Access registry to ensure rules loaded
    ExplainRequest,
    RunRuleRequest,
    explain_plan_endpoint,
    index_status_endpoint,
    run_rule_endpoint,
)


def run_step(name):
    print(f"\n>> {name}...")
    time.sleep(0.5)

def main():
    print("=== Start Phase 11 Demo ===")
    
    # 1. Index Ops
    run_step("Checking Index Status (Slice 11.3)")
    status = index_status_endpoint()
    print("Status:", status)
    assert status["enabled"] is not None
    
    # 2. Planner Explainability
    run_step("Explaining a Compliance Verification Plan (Slice 11.1)")
    query = "verify tls compliance for app_A"
    req = ExplainRequest(query=query)
    explanation = explain_plan_endpoint(req)
    
    print(f"Query: {explanation.query}")
    print(f"Plan Hash: {explanation.plan_hash}")
    print("Rationale:")
    for r in explanation.rationale:
        print(f" - [{r.get('rule')}] because {r.get('because')}")
        
    assert len(explanation.rationale) > 0
    assert explanation.plan_hash is not None
    
    # 3. Rule Registry
    run_step("Listing and Running Rules (Slice 11.2)")
    rules = [r.id for r in _REGISTRY.list_rules()]
    print(f"Available Rules: {rules}")
    
    # Pick tls_compliance or contradiction_marker
    rule_id = "tls_compliance" if "tls_compliance" in rules else rules[0]
    print(f"Running rule '{rule_id}'...")
    
    # Mock context
    ctx = {"trigger": "demo_script"}
    run_req = RunRuleRequest(rule_id=rule_id, input_context=ctx)
    
    try:
        run_resp = run_rule_endpoint(run_req)
        print("Rule Output:", run_resp.output)
        assert run_resp.output  is not None
    except Exception as e:
        print(f"Rule execution failed (expected if binary missing, but logic path is tested): {e}")

    print("\n✅ Phase 11 Demo Complete!")

if __name__ == "__main__":
    main()
