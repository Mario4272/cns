from datetime import datetime, timedelta

import pytest
from dateutil.tz import UTC

from cns_py.cql.contradict import (
    detect_all_contradictions,
    detect_atom_text_contradictions,
    detect_fiber_contradictions,
)
from cns_py.storage.db import get_conn


@pytest.fixture
def setup_contradiction_data():
    """Set up test data with known contradictions."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean up any existing test data (scoped to this test labels only)
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN ("
                " SELECT f.id FROM fibers f "
                " JOIN atoms a_src ON a_src.id=f.src "
                " JOIN atoms a_dst ON a_dst.id=f.dst "
                " WHERE a_src.label LIKE 'TestEntity%' OR a_dst.label LIKE 'TestValue%')"
            )
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN ("
                " SELECT a.id FROM atoms a WHERE a.label LIKE 'TestEntity%')"
            )
            cur.execute(
                "DELETE FROM fibers USING atoms a_src, atoms a_dst "
                " WHERE a_src.id=fibers.src AND a_dst.id=fibers.dst "
                " AND (a_src.label LIKE 'TestEntity%' OR a_dst.label LIKE 'TestValue%')"
            )
            cur.execute(
                "DELETE FROM atoms WHERE label LIKE 'TestEntity%' OR label LIKE 'TestValue%'"
            )

            # Create test atoms
            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Entity", "TestEntity1", "Original text"),
            )
            entity1_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestValue1", "Value A"),
            )
            value1_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestValue2", "Value B"),
            )
            value2_id = cur.fetchone()[0]

            # Create contradicting fibers: entity1 -> value1 and entity1 -> value2
            # Both valid during overlapping time periods
            now = datetime.now(tz=UTC)
            past = now - timedelta(days=30)
            future = now + timedelta(days=30)

            # Fiber 1: entity1 -> value1 (valid from past to future)
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (entity1_id, value1_id, "has_value"),
            )
            fiber1_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('fiber', %s, %s, %s, %s)""",
                (fiber1_id, past, future, 0.9),
            )

            # Fiber 2: entity1 -> value2 (valid from now to future+60)
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (entity1_id, value2_id, "has_value"),
            )
            fiber2_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('fiber', %s, %s, %s, %s)""",
                (fiber2_id, now, future + timedelta(days=60), 0.85),
            )

            # Create atoms with text contradictions
            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Entity", "TestEntity2", "First version of text"),
            )
            atom1_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Entity", "TestEntity2", "Second version of text"),
            )
            atom2_id = cur.fetchone()[0]

            # Add aspects with overlapping validity
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('atom', %s, %s, %s, %s)""",
                (atom1_id, past, now + timedelta(days=15), 0.8),
            )

            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('atom', %s, %s, %s, %s)""",
                (atom2_id, now, future, 0.75),
            )

    yield

    # Cleanup after test (scoped)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN ("
                " SELECT f.id FROM fibers f JOIN atoms a_src ON a_src.id=f.src "
                " JOIN atoms a_dst ON a_dst.id=f.dst "
                " WHERE a_src.label LIKE 'TestEntity%' OR a_dst.label LIKE 'TestValue%')"
            )
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN ("
                " SELECT a.id FROM atoms a WHERE a.label LIKE 'TestEntity%')"
            )
            cur.execute(
                "DELETE FROM fibers USING atoms a_src, atoms a_dst "
                " WHERE a_src.id=fibers.src AND a_dst.id=fibers.dst "
                " AND (a_src.label LIKE 'TestEntity%' OR a_dst.label LIKE 'TestValue%')"
            )
            cur.execute(
                "DELETE FROM atoms WHERE label LIKE 'TestEntity%' OR label LIKE 'TestValue%'"
            )


def test_detect_fiber_contradictions(setup_contradiction_data):
    """Test detection of fiber contradictions."""
    contradictions = detect_fiber_contradictions(subject_label="TestEntity1", predicate="has_value")

    assert len(contradictions) >= 1
    contra = contradictions[0]

    assert contra.subject_label == "TestEntity1"
    assert contra.predicate == "has_value"
    assert {contra.object1_label, contra.object2_label} == {"TestValue1", "TestValue2"}
    assert contra.overlap_start is not None
    assert contra.overlap_end is not None
    assert "overlapping time periods" in contra.reason


def test_detect_atom_text_contradictions(setup_contradiction_data):
    """Test detection of atom text contradictions."""
    contradictions = detect_atom_text_contradictions(kind="Entity", label="TestEntity2")

    assert len(contradictions) >= 1
    contra = contradictions[0]

    assert contra.subject_label == "TestEntity2"
    assert contra.predicate == "text_mismatch"
    assert "First version" in contra.object1_label or "Second version" in contra.object1_label
    assert contra.overlap_start is not None


def test_detect_all_contradictions(setup_contradiction_data):
    """Test detection of all contradiction types."""
    contradictions = detect_all_contradictions(limit=100)

    # Should find both fiber and atom contradictions
    assert len(contradictions) >= 2

    # Check we have different types
    predicates = {c.predicate for c in contradictions}
    assert "has_value" in predicates or "text_mismatch" in predicates


def test_no_contradictions_without_overlap():
    """Test that non-overlapping temporal ranges don't trigger contradictions."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean up (scoped)
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN ("
                " SELECT f.id FROM fibers f JOIN atoms a_src ON a_src.id=f.src "
                " JOIN atoms a_dst ON a_dst.id=f.dst "
                " WHERE a_src.label = 'TestNoOverlap' OR a_dst.label IN ('ValueA','ValueB'))"
            )
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN ("
                " SELECT a.id FROM atoms a WHERE a.label IN ('TestNoOverlap','ValueA','ValueB'))"
            )
            cur.execute(
                "DELETE FROM fibers USING atoms a_src, atoms a_dst "
                " WHERE a_src.id=fibers.src AND a_dst.id=fibers.dst "
                " AND (a_src.label='TestNoOverlap' OR a_dst.label IN ('ValueA','ValueB'))"
            )
            cur.execute("DELETE FROM atoms WHERE label IN ('TestNoOverlap','ValueA','ValueB')")

            # Create entity and values
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id",
                ("Entity", "TestNoOverlap"),
            )
            entity_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id", ("Concept", "ValueA")
            )
            value_a_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES (%s, %s) RETURNING id", ("Concept", "ValueB")
            )
            value_b_id = cur.fetchone()[0]

            now = datetime.now(tz=UTC)
            past = now - timedelta(days=60)
            middle = now - timedelta(days=30)

            # Fiber 1: valid from past to middle
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (entity_id, value_a_id, "has_value"),
            )
            fiber1_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('fiber', %s, %s, %s, %s)""",
                (fiber1_id, past, middle, 0.9),
            )

            # Fiber 2: valid from middle+1 day to now (no overlap)
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (entity_id, value_b_id, "has_value"),
            )
            fiber2_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief)
                   VALUES ('fiber', %s, %s, %s, %s)""",
                (fiber2_id, middle + timedelta(days=1), now, 0.85),
            )

    # Should find no contradictions since ranges don't overlap
    contradictions = detect_fiber_contradictions(subject_label="TestNoOverlap")
    assert len(contradictions) == 0

    # Cleanup (scoped)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN ("
                " SELECT f.id FROM fibers f JOIN atoms a_src ON a_src.id=f.src "
                " JOIN atoms a_dst ON a_dst.id=f.dst "
                " WHERE a_src.label='TestNoOverlap' OR a_dst.label IN ('ValueA','ValueB'))"
            )
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN ("
                " SELECT a.id FROM atoms a WHERE a.label IN ('TestNoOverlap','ValueA','ValueB'))"
            )
            cur.execute(
                "DELETE FROM fibers USING atoms a_src, atoms a_dst "
                " WHERE a_src.id=fibers.src AND a_dst.id=fibers.dst "
                " AND (a_src.label='TestNoOverlap' OR a_dst.label IN ('ValueA','ValueB'))"
            )
            cur.execute("DELETE FROM atoms WHERE label IN ('TestNoOverlap', 'ValueA', 'ValueB')")


def test_detect_contradictions_with_filters():
    """Test that filters work correctly."""
    # Test with non-existent label should return empty
    contradictions = detect_fiber_contradictions(subject_label="NonExistentLabel")
    assert len(contradictions) == 0

    # Test with non-existent predicate should return empty
    contradictions = detect_fiber_contradictions(predicate="non_existent_predicate")
    assert len(contradictions) == 0
