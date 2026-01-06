"""
Unit tests for Retrieval Planner (Slice 10.1).
"""
import pytest
from cns_py.planner.planner import Planner
from cns_py.planner.plan import ExactQueryStep, VectorSearchStep, WasmRuleStep

def test_planner_exact_heuristic():
    planner = Planner()
    plan = planner.plan("id:test_atom_123")
    
    # Should have Exact step AND Vector step (fallback/context)
    assert len(plan.steps) >= 1
    assert isinstance(plan.steps[0], ExactQueryStep)
    assert plan.steps[0].atom_id == "test_atom_123"

def test_planner_vector_default():
    planner = Planner()
    plan = planner.plan("hello world")
    
    # Simple text -> Vector search in default/code determined by router
    # "hello world" -> likely "default"
    assert len(plan.steps) == 1
    assert isinstance(plan.steps[0], VectorSearchStep)
    assert plan.steps[0].space == "default"

def test_planner_vector_code():
    planner = Planner()
    plan = planner.plan("def compute_hash()")
    
    # "def ..." -> likely "code" space
    assert len(plan.steps) == 1
    assert isinstance(plan.steps[0], VectorSearchStep)
    assert plan.steps[0].space == "code"

def test_planner_rule_trigger():
    planner = Planner()
    plan = planner.plan("verify tls compliance")
    
    # Should trigger vector search AND rule step
    has_vector = any(isinstance(s, VectorSearchStep) for s in plan.steps)
    has_rule = any(isinstance(s, WasmRuleStep) for s in plan.steps)
    
    assert has_vector
    assert has_rule
    
    rule_step = next(s for s in plan.steps if isinstance(s, WasmRuleStep))
    assert rule_step.rule_name == "tls_compliance"
