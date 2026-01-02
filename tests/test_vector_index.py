import pytest
import numpy as np
from typing import List
from cns_py.vector.memory_index import ExactInMemoryIndex
# from cns_py.vector.pg_index import PgVectorIndex

def test_memory_index_ops():
    """Test basic upsert, query, delete ops."""
    idx = ExactInMemoryIndex()
    
    # Upsert
    idx.upsert("a", [1.0, 0.0])
    idx.upsert("b", [0.0, 1.0])
    
    # Query exact match
    results = idx.query([1.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0][0] == "a"
    assert abs(results[0][1] - 1.0) < 1e-6 # Score ~1.0
    
    # Delete
    idx.delete("a")
    results = idx.query([1.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0][0] == "b" # Fallback to b
    assert results[0][1] < 0.1 # Orthogonal, score 0.0

def test_memory_index_determinism():
    """Verify deterministic tie-breaking: Score Desc, then ID Asc."""
    idx = ExactInMemoryIndex()
    
    # Two orthogonal vectors, same score (0.0) relative to query [0, 0, 1]?
    # No, let's make them identical to the query for max score tie.
    
    # v1 = [1, 0]
    # v2 = [1, 0] 
    # Query = [1, 0] -> Both score 1.0.
    
    idx.upsert("id_b", [1.0, 0.0])
    idx.upsert("id_a", [1.0, 0.0])
    
    results = idx.query([1.0, 0.0], k=2)
    assert len(results) == 2
    
    # Should get id_a first because "id_a" < "id_b"
    assert results[0][0] == "id_a"
    assert results[1][0] == "id_b"
    
    # Ensure scores are identical
    assert abs(results[0][1] - results[1][1]) < 1e-9

def test_memory_index_normalization():
    """Verify internal normalization."""
    idx = ExactInMemoryIndex()
    
    # Insert unnormalized vector [2, 0] -> effectively [1, 0]
    idx.upsert("a", [2.0, 0.0])
    
    # Query with unnormalized vector [0.5, 0] -> effectively [1, 0]
    results = idx.query([0.5, 0.0], k=1)
    
    assert results[0][0] == "a"
    assert abs(results[0][1] - 1.0) < 1e-6

def test_memory_index_empty():
    idx = ExactInMemoryIndex()
    res = idx.query([1.0, 2.0], k=5)
    assert res == []
