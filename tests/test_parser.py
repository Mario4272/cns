from cns_py.cql.parser import parse


def test_parse_minimal_fields():
    q = parse(
        'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE'
    )
    assert q.label == "FrameworkX"
    assert q.predicate == "supports_tls"
    assert q.asof_iso == "2025-01-01T00:00:00Z"
    assert q.explain is True
    assert q.provenance is True


def test_parse_belief_threshold():
    q = parse('MATCH label="X" BELIEF >= 0.7 RETURN EXPLAIN')
    assert q.belief_ge == 0.7
