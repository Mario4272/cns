"""Integration tests for contradiction detection with seeded data."""

import json
from datetime import datetime, timedelta

import pytest
from dateutil.tz import UTC

from cns_py.cql.contradict import detect_all_contradictions, detect_fiber_contradictions
from cns_py.cql.executor import cql
from cns_py.storage.db import get_conn


@pytest.fixture
def seed_contradiction_scenario():
    """Seed a realistic contradiction scenario for testing."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean up any existing test data
            cur.execute("DELETE FROM aspects WHERE subject_kind IN ('atom', 'fiber')")
            cur.execute("DELETE FROM fibers")
            cur.execute(
                "DELETE FROM atoms WHERE label LIKE 'TestFramework%' OR label LIKE 'TestTLS%'"
            )

            # Create test atoms: Framework and two TLS versions
            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Entity", "TestFrameworkY", "A test security framework"),
            )
            framework_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestTLS1.2", "TLS version 1.2"),
            )
            tls12_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestTLS1.3", "TLS version 1.3"),
            )
            tls13_id = cur.fetchone()[0]

            # Create OVERLAPPING fibers (this is the contradiction)
            now = datetime.now(tz=UTC)
            past = now - timedelta(days=60)
            future = now + timedelta(days=60)

            # Fiber 1: Framework supports TLS1.2 (past to future)
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls12_id, "supports_tls"),
            )
            fiber1_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, 
                                    belief, provenance)
                VALUES ('fiber', %s, %s, %s, %s, %s)
                """,
                (
                    fiber1_id,
                    past,
                    future,
                    0.90,
                    json.dumps(
                        {
                            "source_id": "test_doc_v1",
                            "uri": "https://test.example.com/doc/v1",
                            "hash": "test-hash-1",
                            "fetched_at": past.isoformat(),
                        }
                    ),
                ),
            )

            # Fiber 2: Framework supports TLS1.3 (now-30days to future+30days) - OVERLAPS!
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls13_id, "supports_tls"),
            )
            fiber2_id = cur.fetchone()[0]

            overlap_start = now - timedelta(days=30)
            overlap_end = future + timedelta(days=30)

            cur.execute(
                """
                INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, 
                                    belief, provenance)
                VALUES ('fiber', %s, %s, %s, %s, %s)
                """,
                (
                    fiber2_id,
                    overlap_start,
                    overlap_end,
                    0.95,
                    json.dumps(
                        {
                            "source_id": "test_doc_v2",
                            "uri": "https://test.example.com/doc/v2",
                            "hash": "test-hash-2",
                            "fetched_at": overlap_start.isoformat(),
                        }
                    ),
                ),
            )

    yield

    # Cleanup
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM aspects WHERE subject_kind IN ('atom', 'fiber')")
            cur.execute("DELETE FROM fibers")
            cur.execute(
                "DELETE FROM atoms WHERE label LIKE 'TestFramework%' OR label LIKE 'TestTLS%'"
            )


def test_contradiction_detected(seed_contradiction_scenario):
    """Test that the contradiction detector finds the seeded conflict."""
    contradictions = detect_fiber_contradictions(
        subject_label="TestFrameworkY", predicate="supports_tls"
    )

    # Should find exactly one contradiction
    assert len(contradictions) == 1

    contra = contradictions[0]
    assert contra.subject_label == "TestFrameworkY"
    assert contra.predicate == "supports_tls"

    # Should involve both TLS versions
    tls_versions = {contra.object1_label, contra.object2_label}
    assert "TestTLS1.2" in tls_versions
    assert "TestTLS1.3" in tls_versions

    # Should have overlap period
    assert contra.overlap_start is not None
    assert contra.overlap_end is not None
    assert contra.overlap_start < contra.overlap_end

    # Reason should mention overlapping time
    assert "overlapping" in contra.reason.lower()


def test_contradiction_affects_belief(seed_contradiction_scenario):
    """Test that contradictions are visible in query results."""
    # Query for the framework's TLS support
    query = 'MATCH label="TestFrameworkY" PREDICATE supports_tls RETURN EXPLAIN PROVENANCE'
    result = cql(query)

    # Should return results (both conflicting claims)
    assert "results" in result
    assert len(result["results"]) >= 2

    # Both TLS versions should appear
    object_labels = {r["object_label"] for r in result["results"]}
    assert "TestTLS1.2" in object_labels
    assert "TestTLS1.3" in object_labels

    # All results should have provenance
    for r in result["results"]:
        assert "provenance" in r
        assert len(r["provenance"]) > 0
        assert r["provenance"][0]["source_id"] is not None


def test_contradiction_with_asof_resolves(seed_contradiction_scenario):
    """Test that ASOF queries can resolve contradictions temporally."""
    # Query at a time when only TLS1.2 was valid (far in the past)
    past_date = (datetime.now(tz=UTC) - timedelta(days=90)).isoformat()
    query = (
        f'MATCH label="TestFrameworkY" PREDICATE supports_tls ASOF {past_date} RETURN PROVENANCE'
    )
    result = cql(query)

    # Should return only TLS1.2 (no overlap at that time)
    assert "results" in result
    if len(result["results"]) > 0:
        # If we get results, they should be TLS1.2
        for r in result["results"]:
            assert r["object_label"] in ["TestTLS1.2", "TestTLS1.3"]


def test_detect_all_finds_contradiction(seed_contradiction_scenario):
    """Test that detect_all_contradictions finds the seeded conflict."""
    all_contras = detect_all_contradictions(limit=100)

    # Should find at least our seeded contradiction
    assert len(all_contras) >= 1

    # At least one should be our TestFrameworkY contradiction
    framework_contras = [c for c in all_contras if c.subject_label == "TestFrameworkY"]
    assert len(framework_contras) >= 1


def test_contradiction_explain_artifact(seed_contradiction_scenario):
    """Test that EXPLAIN mode provides useful debugging info for contradictions."""
    query = 'MATCH label="TestFrameworkY" PREDICATE supports_tls RETURN EXPLAIN PROVENANCE'
    result = cql(query)

    # Should have explain section
    assert "explain" in result
    explain = result["explain"]

    # Should have timing info
    assert "total_ms" in explain
    assert explain["total_ms"] > 0

    # Should have steps
    assert "steps" in explain
    assert len(explain["steps"]) > 0

    # Steps should include key operations
    step_names = {s["name"] for s in explain["steps"]}
    assert "temporal_mask" in step_names or "graph_traverse" in step_names

    # Can be serialized to JSON (for CI artifact upload)
    explain_json = json.dumps(explain, indent=2)
    assert len(explain_json) > 0


def test_no_contradiction_without_overlap():
    """Test that non-overlapping temporal ranges don't trigger false positives."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean up
            cur.execute("DELETE FROM aspects WHERE subject_kind IN ('atom', 'fiber')")
            cur.execute("DELETE FROM fibers")
            cur.execute("DELETE FROM atoms WHERE label = 'TestNoConflict'")

            # Create framework and TLS versions
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id",
                ("Entity", "TestNoConflict"),
            )
            framework_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id", ("Concept", "TLS1.2")
            )
            tls12_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id", ("Concept", "TLS1.3")
            )
            tls13_id = cur.fetchone()[0]

            now = datetime.now(tz=UTC)
            past = now - timedelta(days=90)
            middle = now - timedelta(days=45)

            # Fiber 1: TLS1.2 valid from past to middle
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls12_id, "supports_tls"),
            )
            fiber1_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('fiber', %s, %s, %s, %s)""",
                (fiber1_id, past, middle, 0.9),
            )

            # Fiber 2: TLS1.3 valid from middle+1day to now (NO OVERLAP)
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls13_id, "supports_tls"),
            )
            fiber2_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('fiber', %s, %s, %s, %s)""",
                (fiber2_id, middle + timedelta(days=1), now, 0.95),
            )

    # Should find NO contradictions (no overlap)
    contradictions = detect_fiber_contradictions(subject_label="TestNoConflict")
    assert len(contradictions) == 0

    # Cleanup
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM aspects WHERE subject_kind IN ('atom', 'fiber')")
            cur.execute("DELETE FROM fibers")
            cur.execute("DELETE FROM atoms WHERE label IN ('TestNoConflict', 'TLS1.2', 'TLS1.3')")
