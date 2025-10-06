"""Property-based tests for CQL parser using hypothesis."""
from hypothesis import given, strategies as st

from cns_py.cql.parser import parse


# Strategy for generating valid labels
labels = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd"),
    whitelist_characters="_-"
))

# Strategy for generating valid predicates
predicates = st.text(min_size=1, max_size=30, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd"),
    whitelist_characters="_"
))

# Strategy for generating valid ISO8601 timestamps
timestamps = st.datetimes(
    min_value=st.datetime(2000, 1, 1),
    max_value=st.datetime(2030, 12, 31)
).map(lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

# Strategy for generating valid belief thresholds
beliefs = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@given(label=labels)
def test_parse_label_roundtrip(label):
    """Property: Parsing a MATCH with label should preserve the label."""
    query = f'MATCH label="{label}" RETURN'
    result = parse(query)
    assert result.label == label


@given(label=labels, predicate=predicates)
def test_parse_label_and_predicate(label, predicate):
    """Property: Parsing MATCH with label and predicate should preserve both."""
    query = f'MATCH label="{label}" PREDICATE {predicate} RETURN'
    result = parse(query)
    assert result.label == label
    assert result.predicate == predicate


@given(label=labels, timestamp=timestamps)
def test_parse_asof_preserves_timestamp(label, timestamp):
    """Property: ASOF timestamp should be preserved exactly."""
    query = f'MATCH label="{label}" ASOF {timestamp} RETURN'
    result = parse(query)
    assert result.label == label
    assert result.asof_iso == timestamp


@given(label=labels, belief=beliefs)
def test_parse_belief_threshold(label, belief):
    """Property: BELIEF threshold should be preserved."""
    query = f'MATCH label="{label}" BELIEF >= {belief} RETURN'
    result = parse(query)
    assert result.label == label
    assert result.belief_ge is not None
    # Allow small floating point differences
    assert abs(result.belief_ge - belief) < 0.0001


@given(label=labels, predicate=predicates, timestamp=timestamps, belief=beliefs)
def test_parse_full_query(label, predicate, timestamp, belief):
    """Property: Full query with all clauses should preserve all values."""
    query = f'MATCH label="{label}" PREDICATE {predicate} ASOF {timestamp} BELIEF >= {belief} RETURN EXPLAIN PROVENANCE'
    result = parse(query)
    assert result.label == label
    assert result.predicate == predicate
    assert result.asof_iso == timestamp
    assert result.belief_ge is not None
    assert abs(result.belief_ge - belief) < 0.0001
    assert result.explain is True
    assert result.provenance is True


def test_parse_minimal_query():
    """Property: Minimal query should have sensible defaults."""
    query = 'MATCH label="X" RETURN'
    result = parse(query)
    assert result.label == "X"
    assert result.predicate is None
    assert result.asof_iso is None
    assert result.belief_ge is None
    assert result.explain is True  # Default
    assert result.provenance is True  # Default


def test_parse_empty_components():
    """Property: Parser should handle edge cases gracefully."""
    # Just MATCH with no other clauses
    result = parse('MATCH label="Test"')
    assert result.label == "Test"
    
    # RETURN without MATCH should still parse (even if semantically invalid)
    result = parse('RETURN EXPLAIN')
    assert result.explain is True
