from datetime import datetime, timedelta, timezone

import pytest

from cns_py.cql.belief_explain import BeliefExplainer


def test_explain_decay():
    explainer = BeliefExplainer()
    # 1 year old
    old = datetime.now(timezone.utc) - timedelta(days=365)

    exp = explainer.explain(1.0, old, 0, 0)

    assert exp.final_score > 0.49 and exp.final_score < 0.51
    # Check steps
    assert exp.steps[0].name == "Base Belief"
    assert exp.steps[1].name == "Time Decay"
    assert "x0.5" in exp.steps[1].impact


def test_explain_contradiction():
    explainer = BeliefExplainer()
    now = datetime.now(timezone.utc)

    exp = explainer.explain(1.0, now, 0, 1)  # 1 contradiction

    # 1.0 * 1.0 * (1 - 0.5) = 0.5
    assert exp.final_score == pytest.approx(0.5)
    # Find contradiction step
    step = next(s for s in exp.steps if s.name == "Contradictions")
    assert "x0.5" in step.impact
    assert "1 contradictions" in step.description


def test_explain_provenance_boost():
    explainer = BeliefExplainer()
    now = datetime.now(timezone.utc)

    # Base 0.5, Prov 4 (+0.4) -> 0.9
    exp = explainer.explain(0.5, now, 4, 0)

    assert exp.final_score == pytest.approx(0.9)
    step = next(s for s in exp.steps if s.name == "Provenance Boost")
    assert "+0.4" in step.impact
