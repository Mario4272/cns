
"""
Demo Script for Phase 12: Belief Revision.
Demonstrates:
1. Belief Calculation (Decay/Penalty)
2. Explanation API (Walkthrough)
3. Integration with Graph API
"""
import sys
import json
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.append(".")

from cns_py.cql.belief import compute_effective_belief, BeliefConfig
from cns_py.cql.belief_explain import BeliefExplainer

def print_section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

def demo_direct_calculation():
    print_section("1. Direct Belief Calculation")
    
    cfg = BeliefConfig()
    print(f"Config: Halflife={cfg.decay_halflife_days}d, Penalty={cfg.contradiction_penalty}")
    
    # Case A: Brand new fact
    now = datetime.now(timezone.utc)
    res, _ = compute_effective_belief(1.0, now, 0, 0, cfg)
    print(f"Case A (New Fact): 1.0 -> {res:.4f}")
    
    # Case B: 1 Year Old Fact
    old = now - timedelta(days=365)
    res, _ = compute_effective_belief(1.0, old, 0, 0, cfg)
    print(f"Case B (1 Year Old): 1.0 -> {res:.4f} (Expected ~0.5)")
    
    # Case C: Contradicted Fact
    res, _ = compute_effective_belief(1.0, now, 0, 1, cfg)
    print(f"Case C (Contradicted): 1.0 -> {res:.4f} (Penalty applied)")

def demo_explanation():
    print_section("2. Belief Explanation Trace")
    explainer = BeliefExplainer()
    
    # explain a complex case
    old = datetime.now(timezone.utc) - timedelta(days=180) # 6 months
    explanation = explainer.explain(
        base_belief=0.9,
        observed_at=old,
        provenance_count=3,
        contradiction_count=0
    )
    
    print(f"Final Score: {explanation.final_score:.4f}")
    print("Trace:")
    for step in explanation.steps:
        print(f"  [{step.name:<16}] {step.impact:<6} -> {step.value_after:.4f} ({step.description})")

def main():
    demo_direct_calculation()
    demo_explanation()
    print("\nPhase 12 Demo Complete.")

if __name__ == "__main__":
    main()
