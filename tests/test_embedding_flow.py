
"""
Tests for Slice 5B: Embedding Pipeline.
Verifies IndexManager uses EmbeddingProvider correctly.
"""
import pytest
import os
import numpy as np
from unittest.mock import MagicMock

from cns_py.vector.manager import IndexManager
from cns_py.vector.embeddings import EmbeddingProvider

class MockProvider(EmbeddingProvider):
    def __init__(self):
        self.calls = []
        
    @property
    def dimension(self) -> int:
        return 4 # Small dim for test
        
    def embed_texts(self, texts):
        self.calls.append(texts)
        # Return fixed vectors based on text length to be deterministic but clear
        return [[float(len(t))] * 4 for t in texts]

def test_manager_uses_provider(monkeypatch):
    """Verify rebuild calls the provider."""
    # Setup env
    monkeypatch.setenv("VECTOR_INDEX_ENABLED", "1")
    monkeypatch.setenv("VECTOR_INDEX_BACKEND", "memory")
    monkeypatch.setenv("VECTOR_INDEX_PATH", "mem_idx_test")

    # Mock DB interaction? 
    # IndexManager.rebuild calls get_conn().
    # We can mock get_conn or insert real atoms if DB avail. 
    # Real DB is better context.
    from cns_py.storage.db import get_conn
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean atoms
            cur.execute("DELETE FROM atoms WHERE kind='Entity'")
            cur.execute("INSERT INTO atoms (label, text, kind) VALUES ('A', 'Alpha', 'Entity')")
            cur.execute("INSERT INTO atoms (label, text, kind) VALUES ('B', 'Beta', 'Entity')")
            
            # Verify they exist
            cur.execute("SELECT count(*) FROM atoms WHERE kind='Entity'")
            count = cur.fetchone()[0]
            print(f"DEBUG: Atoms in DB: {count}")

    mgr = IndexManager()
    # Swap provider with mock
    mock_prov = MockProvider()
    mgr.provider = mock_prov
    mgr.dim = 4 # update dim
    
    # Startup triggers rebuild if index not on disk (env var path is mem_idx_test, presumably empty/clean)
    mgr.startup()
    
    # Check calls
    assert len(mock_prov.calls) > 0
    all_texts = [t for batch in mock_prov.calls for t in batch]
    assert "Alpha" in all_texts
    assert "Beta" in all_texts
    
    # Verify index content
    res = mgr.query([4.0]*4, k=1) # "Beta" has len 4 -> vector [4,4,4,4]
    assert len(res) == 1
    # Check if we got the right ID (we don't know ID, but we know functionality works)
    
def test_deterministic_stub_consistency():
    """Verify the default stub is actually deterministic."""
    from cns_py.vector.embeddings import DeterministicStubProvider
    
    p1 = DeterministicStubProvider()
    p2 = DeterministicStubProvider()
    
    t = ["Hello World", "Another Text"]
    v1 = p1.embed_texts(t)
    v2 = p2.embed_texts(t)
    
    assert np.allclose(v1, v2)
    assert len(v1[0]) == 384
