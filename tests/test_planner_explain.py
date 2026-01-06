"""
Tests for Planner Explainability (Slice 11.1).
Verifies that the /planner/explain endpoint returns deterministic hashes and correct rationale.
"""
from cns_py.api.server import ExplainRequest, explain_plan_endpoint
from cns_py.planner import PlanExplainer, PlanExplanation


def test_explain_plan_structure():
    explainer = PlanExplainer()
    query = "id:123"
    explanation = explainer.explain(query)
    
    # Check typing
    assert isinstance(explanation, PlanExplanation)
    assert explanation.query == query
    assert explanation.determinism is True
    assert explanation.plan_hash is not None
    assert len(explanation.plan_hash) == 64 # SHA256 hex
    
    # Check content
    plan_dict = explanation.plan
    assert plan_dict["query_raw"] == query
    assert len(plan_dict["steps"]) > 0
    assert plan_dict["steps"][0]["step_type"] == "exact"
    
    # Check rationale
    rationale = explanation.rationale
    assert len(rationale) > 0
    assert rationale[0]["rule"] == "ExactMatchHeuristic"

def test_plan_hash_determinism():
    explainer = PlanExplainer()
    query = "verify tls compliance for app_A"
    
    exp1 = explainer.explain(query)
    exp2 = explainer.explain(query)
    
    assert exp1.plan_hash == exp2.plan_hash
    assert exp1.plan == exp2.plan
    assert exp1.rationale == exp2.rationale

def test_explain_endpoint_integration():
    req = ExplainRequest(query="verify policy")
    resp = explain_plan_endpoint(req)
    
    assert resp.plan_hash is not None
    # Check logic trigger
    # "verify policy" should trigger ComplianceHeuristic
    has_compliance = False
    for r in resp.rationale:
        if r["rule"] == "ComplianceHeuristic":
            has_compliance = True
            break
    assert has_compliance
