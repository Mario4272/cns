from __future__ import annotations

from cns_py.cql.parser import parse


def test_parse_ignores_unknown_tokens_and_incomplete_clauses():
    q = parse("FOO BAR MATCH LABEL RETURN EXPLAIN PROVENANCE")
    # Current parser treats LABEL <next-token> as value; here it becomes 'RETURN'
    assert q.label == "RETURN"
    assert q.explain is True and q.provenance is True


def test_parse_incomplete_label_at_end_is_ignored():
    # LABEL at end has no following token; parser should keep label None
    q = parse("MATCH LABEL")
    assert q.label is None


def test_parse_lowercase_and_spacing_variants():
    q = parse('match label="A" predicate supports_tls return explain provenance')
    assert q.label == "A"
    assert q.predicate == "supports_tls"
    assert q.explain is True and q.provenance is True


def test_parse_belief_without_comparator_is_ignored():
    q = parse("BELIEF 0.8 RETURN EXPLAIN PROVENANCE")
    assert q.belief_ge is None


def test_parse_asof_followed_by_return_sets_value_to_return():
    q = parse("ASOF RETURN EXPLAIN PROVENANCE")
    assert q.asof_iso == "RETURN"


def test_parse_asof_at_end_is_ignored():
    q = parse("MATCH LABEL X ASOF")
    assert q.asof_iso is None
