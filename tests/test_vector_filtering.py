from cns_py.vector.memory_index import ExactInMemoryIndex


def test_filtering_exclusivity():
    """Verify that filter excludes non-matching documents."""
    idx = ExactInMemoryIndex()
    idx.upsert("a", [1.0, 0.0], metadata={"kind": "A", "tag": "red"})
    idx.upsert("b", [0.0, 1.0], metadata={"kind": "B", "tag": "blue"})
    idx.upsert("c", [1.0, 0.0], metadata={"kind": "A", "tag": "blue"})
    
    # Query for kind=A
    res = idx.query([1.0, 0.0], k=10, filter={"kind": "A"})
    ids = {r[0] for r in res}
    assert "a" in ids
    assert "c" in ids
    assert "b" not in ids
    
    # Query for tag=blue
    res = idx.query([1.0, 0.0], k=10, filter={"tag": "blue"})
    ids = {r[0] for r in res}
    assert "b" in ids
    assert "c" in ids
    assert "a" not in ids
    
    # Query for kind=A AND tag=blue
    res = idx.query([1.0, 0.0], k=10, filter={"kind": "A", "tag": "blue"})
    ids = {r[0] for r in res}
    assert "c" in ids
    assert "a" not in ids
    assert "b" not in ids

def test_filtering_with_missing_metadata():
    """Documents without metadata should be excluded if filter is present."""
    idx = ExactInMemoryIndex()
    idx.upsert("a", [1.0, 0.0], metadata={"kind": "A"})
    idx.upsert("b", [1.0, 0.0]) # No metadata
    
    res = idx.query([1.0, 0.0], k=10, filter={"kind": "A"})
    ids = {r[0] for r in res}
    assert "a" in ids
    assert "b" not in ids

def test_filtering_determinism():
    """Filtered results should still respect tie-breaking rules."""
    idx = ExactInMemoryIndex()
    # a and c match query [1,0] perfectly.
    idx.upsert("id_c", [1.0, 0.0], metadata={"kind": "A"}) 
    idx.upsert("id_a", [1.0, 0.0], metadata={"kind": "A"})
    
    res = idx.query([1.0, 0.0], k=2, filter={"kind": "A"})
    assert res[0][0] == "id_a" # ID asc
    assert res[1][0] == "id_c"

def test_filtering_no_matches():
    idx = ExactInMemoryIndex()
    idx.upsert("a", [1.0, 0.0], metadata={"kind": "A"})
    res = idx.query([1.0, 0.0], k=10, filter={"kind": "B"})
    assert res == []
