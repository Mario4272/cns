"""
Regression tests for Phase 13.1 Determinism.
Ensures identical inputs produce bit-for-bit identical outputs.
"""
import pytest
from cns_py.graph import traverse_from
from cns_py.cql.executor import cql
from cns_py.storage.db import get_conn

@pytest.fixture(scope="module")
def seeded_determinism_graph():
    """Ensure a known graph state exists for testing."""
    # We assume standard seed data exists or we inject transient data.
    # For now, we rely on the existence of 'FrameworkX' from standard demos.
    # If not present, these tests might skip or fail, but in dev env it should be there.
    pass

def test_traverse_determinism_repeated():
    """
    Verify that traverse_from returns exactly the same list of edges
    in exactly the same order across multiple runs.
    """
    # Find ID for FrameworkX
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM atoms WHERE label='FrameworkX' LIMIT 1")
            row = cur.fetchone()
            if not row:
                pytest.skip("FrameworkX not found, skipping determinism test")
            fw_id = row[0]

    # Run 10 times
    results = []
    for _ in range(10):
        # Request a limit that might trigger non-det cutoffs if unsorted
        edges = traverse_from([fw_id], hops=1, limit=5)
        results.append(edges)

    ref = results[0]
    for i, res in enumerate(results[1:]):
        assert res == ref, f"Run {i+1} differed from Run 0"

def test_cql_determinism_complex():
    """
    Verify CQL executor result stability, including provenance order.
    """
    q = 'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2024-12-31T12:00:00Z RETURN PROVENANCE'
    
    # Warmup
    cql(q)
    
    results = []
    for _ in range(10):
        # Convert to JSON string or hash to check deep equality including field order if serialized
        # Here we just check the dict structure equality
        res = cql(q)
        # Remove timing fields which are inherently non-deterministic
        if "explain" in res:
            res["explain"]["total_ms"] = 0
            for step in res["explain"]["steps"]:
                step["ms"] = 0
        
        results.append(res)
        
    ref = results[0]
    for i, res in enumerate(results[1:]):
        # We perform a strict equality check
        assert res == ref, f"CQL Run {i+1} output mismatch"
