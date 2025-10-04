from cns_py.cql.executor import cql


def test_cql_returns_citations_and_explain():
    out = cql('MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE')
    assert 'results' in out and len(out['results']) >= 1
    # at least one citation per result
    for r in out['results']:
        assert isinstance(r.get('provenance'), list)
        assert len(r['provenance']) >= 1
    # explain present
    assert 'explain' in out
    assert isinstance(out['explain'].get('steps'), list)
