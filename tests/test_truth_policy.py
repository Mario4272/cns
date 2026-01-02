"""
Tests for Truth Policy Edge Cases (Task C).
Covers:
  C1: Latest tie-break (observed_at DESC, then ID ASC)
  C2: NULL confidence (treated as 0.0, then ID ASC)
  C3: Contradiction behavior stability
"""

import json
from datetime import datetime, timedelta

import pytest
from dateutil.tz import UTC

from cns_py.cql.contradict import detect_fiber_contradictions
from cns_py.cql.executor import cql
from cns_py.storage.db import get_conn


@pytest.fixture
def clean_truth_policy_data():
    """Clean slate for truth policy tests."""
    prefix = "TestTruthPolicy"

    yield prefix

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN (
                     SELECT id FROM atoms WHERE label LIKE %s
                   )""",
                (f"{prefix}%",),
            )
            # Delete fibers associated with these atoms
            cur.execute(
                """DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN (
                     SELECT f.id FROM fibers f
                     JOIN atoms s ON f.src = s.id
                     WHERE s.label LIKE %s
                   )""",
                (f"{prefix}%",),
            )
            cur.execute(
                """DELETE FROM fibers USING atoms s
                   WHERE fibers.src = s.id AND s.label LIKE %s""",
                (f"{prefix}%",),
            )
            cur.execute("DELETE FROM atoms WHERE label LIKE %s", (f"{prefix}%",))


def test_c1_latest_tie_break(clean_truth_policy_data):
    """
    C1: Latest tie-break.
    Scenario:
      Verify that among multiple items, the one with LATEST observed_at wins.
      If observed_at is TIE, the one with LOWER ID wins (Stable).
    """
    prefix = clean_truth_policy_data

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Create Source
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_S",),
            )
            s_id = cur.fetchone()[0]

            # Create Dests
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_D1",),
            )
            d1_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_D2",),
            )
            d2_id = cur.fetchone()[0]

            # Create Fibers
            # We insert D1 first, D2 second so D1 usually has lower ID.
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'rel') RETURNING id",
                (s_id, d1_id),
            )
            f1_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'rel') RETURNING id",
                (s_id, d2_id),
            )
            f2_id = cur.fetchone()[0]

            # Case 1: Distinct Observed Time
            # F2 is newer => F2 shoud win (even with equal belief)
            now = datetime.now(UTC)
            t_old = now - timedelta(hours=1)
            t_new = now

            # Insert Aspects
            # Both belief=0.5
            prov = json.dumps({"source_id": "test_src"})
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, 0.5, %s, %s)",
                (f1_id, t_old, prov),
            )
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, 0.5, %s, %s)",
                (f2_id, t_new, prov),
            )

    q = f'MATCH label="{prefix}_S" PREDICATE rel RETURN PROVENANCE'

    for i in range(10):
        res = cql(q)
        results = res["results"]
        assert len(results) == 2
        # Winner should be F2 (newer)
        assert results[0]["fiber_id"] == f2_id
        assert results[1]["fiber_id"] == f1_id


def test_c1_tie_break_exact_timestamp(clean_truth_policy_data):
    """
    Scenario: Beliefs equal. Observed_at equal.
    Rule: STABLE ID (ASC) wins.
    """
    prefix = clean_truth_policy_data
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_S_Tie",),
            )
            s_id = cur.fetchone()[0]

            # Dests
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_D1",),
            )
            d1_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_D2",),
            )
            d2_id = cur.fetchone()[0]

            # Fibers
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'rel') RETURNING id",
                (s_id, d1_id),
            )
            f1_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'rel') RETURNING id",
                (s_id, d2_id),
            )
            f2_id = cur.fetchone()[0]

            low_id = min(f1_id, f2_id)
            high_id = max(f1_id, f2_id)

            t_fixed = datetime.now(UTC)

            # Insert Aspects (Equal belief, Equal time)
            prov = json.dumps({"source_id": "test_tie"})
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, 0.5, %s, %s)",
                (f1_id, t_fixed, prov),
            )
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, 0.5, %s, %s)",
                (f2_id, t_fixed, prov),
            )

    q = f'MATCH label="{prefix}_S_Tie" PREDICATE rel RETURN PROVENANCE'

    # 10x Run
    for i in range(10):
        res = cql(q)
        results = res["results"]
        assert len(results) == 2
        # Lowest ID first
        assert results[0]["fiber_id"] == low_id
        assert results[1]["fiber_id"] == high_id


def test_c2_null_confidence(clean_truth_policy_data):
    """
    C2: NULL vs 0.0 vs Positive.
    Rule: NULL treated as 0.0. Tie-break ID ASC.
    """
    prefix = clean_truth_policy_data
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_S_Null",),
            )
            s_id = cur.fetchone()[0]

            # Atoms for dests
            d_ids = []
            for k in range(3):
                cur.execute(
                    "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                    (f"{prefix}_D{k}",),
                )
                d_ids.append(cur.fetchone()[0])

            # Ensure fibers created in known order so we know which ID is which
            # Actually we just capture IDs
            f_ids = []
            for did in d_ids:
                cur.execute(
                    "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'rel') RETURNING id",
                    (s_id, did),
                )
                f_ids.append(cur.fetchone()[0])

            f_ids.sort()  # Ensure we know strict ordering
            f_pos, f_zero, f_null = f_ids[0], f_ids[1], f_ids[2]

            # Assign roles to strictly ordered IDs to test the logic
            # Scenario:
            # f_pos (lowest ID) -> gets Belief 0.2 (Should WIN because belief > 0)
            # f_zero (mid ID) -> gets Belief 0.0
            # f_null (high ID) -> gets Belief NULL
            #
            # Expected order: f_pos, f_zero, f_null
            # Wait, 0.0 and NULL are tied at 0.0. So tie-break is ID.
            # f_zero < f_null. So f_zero comes before f_null.
            # Result: f_pos, f_zero, f_null

            # What if we swap zero/null IDs?
            # Let's try to make NULL have LOWER ID than Zero, to prove ID tie break works.
            # Re-assign:
            f_null = f_ids[1]  # Mid ID
            f_zero = f_ids[2]  # High ID
            f_pos = f_ids[0]  # Low ID

            t_fixed = datetime.now(UTC)
            prov = json.dumps({"source_id": "test_null"})

            # 1. Positive 0.2
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, 0.2, %s, %s)",
                (f_pos, t_fixed, prov),
            )
            # 2. Zero 0.0
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, 0.0, %s, %s)",
                (f_zero, t_fixed, prov),
            )
            # 3. NULL
            cur.execute(
                "INSERT INTO aspects(subject_kind, subject_id, belief, observed_at, provenance) "
                "VALUES ('fiber', %s, NULL, %s, %s)",
                (f_null, t_fixed, prov),
            )

    q = f'MATCH label="{prefix}_S_Null" PREDICATE rel RETURN PROVENANCE'

    for i in range(10):
        res = cql(q)
        results = res["results"]
        assert len(results) == 3

        # 1. Positive wins
        assert results[0]["fiber_id"] == f_pos

        # 2. Null vs Zero: Both effectively 0.0.
        # Tie-break: ID ASC.
        # f_null has ID[1], f_zero has ID[2].
        # So f_null should come before f_zero
        assert results[1]["fiber_id"] == f_null
        assert results[2]["fiber_id"] == f_zero


def test_c3_contradiction_stability(clean_truth_policy_data):
    """
    C3: Contradiction behavior.
    Scenario: Conflicting claims (Overlap).
    Assert:
      1. Contradiction detected.
      2. Query returns both roughly "tied" claims in stable order.
    """
    prefix = clean_truth_policy_data
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_S_Con",),
            )
            s_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_Obj1",),
            )
            o1_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO atoms(kind, label) VALUES ('Entity', %s) RETURNING id",
                (f"{prefix}_Obj2",),
            )
            o2_id = cur.fetchone()[0]

            # Conflicting predicate 'is_valid'
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'is_valid') RETURNING id",
                (s_id, o1_id),
            )
            f1_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, 'is_valid') RETURNING id",
                (s_id, o2_id),
            )
            f2_id = cur.fetchone()[0]

            low_id = min(f1_id, f2_id)
            high_id = max(f1_id, f2_id)

            # Make them overlap in time
            now = datetime.now(UTC)

            # F1: valid now (0.8 belief)
            # F2: valid now (0.8 belief) - Exact tie in logic
            prov = json.dumps({"source_id": "test_con"})
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief,
                                      observed_at, provenance)
                   VALUES ('fiber', %s, %s, %s, 0.8, %s, %s)""",
                (f1_id, now - timedelta(days=1), now + timedelta(days=1), now, prov),
            )
            cur.execute(
                """INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief,
                                      observed_at, provenance)
                   VALUES ('fiber', %s, %s, %s, 0.8, %s, %s)""",
                (f2_id, now - timedelta(days=1), now + timedelta(days=1), now, prov),
            )

    # 1. Detect Contradictions
    contras = detect_fiber_contradictions(subject_label=f"{prefix}_S_Con", predicate="is_valid")
    assert len(contras) == 1
    c = contras[0]
    assert c.subject_label == f"{prefix}_S_Con"
    assert "TestTruthPolicy_Obj1" in {c.object1_label, c.object2_label}

    # 2. Query Stability
    q = f'MATCH label="{prefix}_S_Con" PREDICATE is_valid RETURN PROVENANCE'
    for i in range(10):
        res = cql(q)
        results = res["results"]
        assert len(results) == 2

        # Tie-break rule should apply: ID ASC
        assert results[0]["fiber_id"] == low_id
        assert results[1]["fiber_id"] == high_id
