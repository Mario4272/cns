import pytest
import numpy as np
import os
import shutil
from cns_py.vector.memory_index import ExactInMemoryIndex

@pytest.fixture
def temp_index_path(tmp_path):
    """Fixture for temporary index path prefix."""
    path = tmp_path / "test_index"
    return str(path)

def test_memory_index_roundtrip(temp_index_path):
    """Verify save and load reconstructs the index exactly."""
    idx = ExactInMemoryIndex()
    # Seed data
    idx.upsert("a", [1.0, 0.0], metadata={"kind": "test"})
    idx.upsert("b", [0.0, 1.0], metadata={"kind": "other"})
    
    # Save
    idx.save(temp_index_path)
    
    # Check files exist
    assert os.path.exists(f"{temp_index_path}.npz")
    assert os.path.exists(f"{temp_index_path}.meta.json")
    
    # Load into new index
    idx2 = ExactInMemoryIndex()
    idx2.load(temp_index_path)
    
    # Verify content
    res_a = idx2.query([1.0, 0.0], k=1)
    assert res_a[0][0] == "a"
    assert abs(res_a[0][1] - 1.0) < 1e-6
    
    res_b = idx2.query([0.0, 1.0], k=1)
    assert res_b[0][0] == "b"
    assert abs(res_b[0][1] - 1.0) < 1e-6
    
    # Verify Metadata (not exposed in query directly yet, but check internal)
    assert idx2._metadata["a"]["kind"] == "test"

def test_memory_index_roundtrip_determinism(temp_index_path):
    """Verify that loaded index preserves deterministic tie-breaking."""
    idx = ExactInMemoryIndex()
    # Identical vectors
    idx.upsert("id_b", [1.0, 0.0])
    idx.upsert("id_a", [1.0, 0.0])
    
    idx.save(temp_index_path)
    
    idx2 = ExactInMemoryIndex()
    idx2.load(temp_index_path)
    
    results = idx2.query([1.0, 0.0], k=2)
    # id_a < id_b
    assert results[0][0] == "id_a"
    assert results[1][0] == "id_b"

def test_memory_index_version_check(temp_index_path):
    """Verify correct version handling."""
    idx = ExactInMemoryIndex()
    idx.save(temp_index_path)
    
    # Corrupt version
    import json
    with open(f"{temp_index_path}.meta.json", "r") as f:
        meta = json.load(f)
    meta["version"] = "v999"
    with open(f"{temp_index_path}.meta.json", "w") as f:
        json.dump(meta, f)
        
    idx2 = ExactInMemoryIndex()
    with pytest.raises(ValueError, match="Unknown index version"):
        idx2.load(temp_index_path)
