from __future__ import annotations

from cns_py.cql.parser import parse


def test_parse_defaults_minimal_query():
    q = parse("RETURN EXPLAIN PROVENANCE")
    assert q.label is None
    assert q.predicate is None
    assert q.asof_iso is None
    assert q.belief_ge is None
    assert q.explain is True
    assert q.provenance is True


def test_parse_label_equals_and_plain():
    q1 = parse('MATCH label="Foo" RETURN EXPLAIN PROVENANCE')
    q2 = parse("MATCH LABEL Foo RETURN EXPLAIN PROVENANCE")
    assert q1.label == "Foo"
    assert q2.label == "Foo"


def test_parse_predicate_and_asof_and_belief_ge():
    q = parse(
        'MATCH label="X" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z BELIEF >= 0.7 "
        "RETURN EXPLAIN PROVENANCE"
    )
    assert q.label == "X"
    assert q.predicate == "supports_tls"
    assert q.asof_iso == "2025-01-01T00:00:00Z"
    assert q.belief_ge == 0.7


def test_parse_belief_gt_alias_and_invalid_number():
    q1 = parse("BELIEF > 0.9 RETURN EXPLAIN PROVENANCE")
    assert q1.belief_ge == 0.9

    q2 = parse("BELIEF >= notanumber RETURN EXPLAIN PROVENANCE")
    # invalid number should be ignored safely
    assert q2.belief_ge is None
