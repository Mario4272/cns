from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from cns_py.storage.db import get_conn


@dataclass
class Contradiction:
    """Represents a detected contradiction between two atoms or fibers."""
    subject_id: int
    subject_label: str
    predicate: str
    object1_id: int
    object1_label: str
    object2_id: int
    object2_label: str
    overlap_start: Optional[datetime]
    overlap_end: Optional[datetime]
    reason: str


def detect_fiber_contradictions(
    subject_label: Optional[str] = None,
    predicate: Optional[str] = None,
    limit: int = 100
) -> List[Contradiction]:
    """
    Detect simple contradictions: same subject+predicate pointing to different objects
    with overlapping temporal validity.
    
    Args:
        subject_label: Filter by source atom label (optional)
        predicate: Filter by fiber predicate (optional)
        limit: Maximum contradictions to return
    
    Returns:
        List of Contradiction objects
    """
    sql = """
    SELECT 
        a_src.id AS subject_id,
        a_src.label AS subject_label,
        f1.predicate AS predicate,
        a_dst1.id AS object1_id,
        a_dst1.label AS object1_label,
        a_dst2.id AS object2_id,
        a_dst2.label AS object2_label,
        GREATEST(
            COALESCE(asp1.valid_from, '-infinity'::timestamptz),
            COALESCE(asp2.valid_from, '-infinity'::timestamptz)
        ) AS overlap_start,
        LEAST(
            COALESCE(asp1.valid_to, 'infinity'::timestamptz),
            COALESCE(asp2.valid_to, 'infinity'::timestamptz)
        ) AS overlap_end
    FROM fibers f1
    JOIN fibers f2 ON f1.src = f2.src AND f1.predicate = f2.predicate AND f1.id < f2.id
    JOIN atoms a_src ON a_src.id = f1.src
    JOIN atoms a_dst1 ON a_dst1.id = f1.dst
    JOIN atoms a_dst2 ON a_dst2.id = f2.dst
    JOIN aspects asp1 ON asp1.subject_kind='fiber' AND asp1.subject_id=f1.id
    JOIN aspects asp2 ON asp2.subject_kind='fiber' AND asp2.subject_id=f2.id
    WHERE f1.dst != f2.dst
      AND COALESCE(asp1.valid_from, '-infinity'::timestamptz) < COALESCE(asp2.valid_to, 'infinity'::timestamptz)
      AND COALESCE(asp2.valid_from, '-infinity'::timestamptz) < COALESCE(asp1.valid_to, 'infinity'::timestamptz)
    """
    
    params = {}
    where_clauses = []
    
    if subject_label is not None:
        where_clauses.append("a_src.label = %(subject_label)s")
        params["subject_label"] = subject_label
    
    if predicate is not None:
        where_clauses.append("f1.predicate = %(predicate)s")
        params["predicate"] = predicate
    
    if where_clauses:
        sql += " AND " + " AND ".join(where_clauses)
    
    sql += f" LIMIT {limit}"
    
    contradictions: List[Contradiction] = []
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for row in cur.fetchall():
                (subj_id, subj_label, pred, obj1_id, obj1_label, 
                 obj2_id, obj2_label, overlap_start, overlap_end) = row
                
                reason = f"Same subject '{subj_label}' has predicate '{pred}' pointing to both '{obj1_label}' and '{obj2_label}' during overlapping time periods"
                
                contradictions.append(
                    Contradiction(
                        subject_id=subj_id,
                        subject_label=subj_label,
                        predicate=pred,
                        object1_id=obj1_id,
                        object1_label=obj1_label,
                        object2_id=obj2_id,
                        object2_label=obj2_label,
                        overlap_start=overlap_start,
                        overlap_end=overlap_end,
                        reason=reason
                    )
                )
    
    return contradictions


def detect_atom_text_contradictions(
    kind: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = 100
) -> List[Contradiction]:
    """
    Detect contradictions in atom text fields: same kind+label with different text
    values during overlapping temporal validity.
    
    Args:
        kind: Filter by atom kind (Entity, Concept, Rule, Program)
        label: Filter by atom label
        limit: Maximum contradictions to return
    
    Returns:
        List of Contradiction objects
    """
    sql = """
    SELECT 
        a1.id AS atom1_id,
        a1.label AS atom1_label,
        a1.text AS text1,
        a2.id AS atom2_id,
        a2.label AS atom2_label,
        a2.text AS text2,
        GREATEST(
            COALESCE(asp1.valid_from, '-infinity'::timestamptz),
            COALESCE(asp2.valid_from, '-infinity'::timestamptz)
        ) AS overlap_start,
        LEAST(
            COALESCE(asp1.valid_to, 'infinity'::timestamptz),
            COALESCE(asp2.valid_to, 'infinity'::timestamptz)
        ) AS overlap_end
    FROM atoms a1
    JOIN atoms a2 ON a1.kind = a2.kind AND a1.label = a2.label AND a1.id < a2.id
    LEFT JOIN aspects asp1 ON asp1.subject_kind='atom' AND asp1.subject_id=a1.id
    LEFT JOIN aspects asp2 ON asp2.subject_kind='atom' AND asp2.subject_id=a2.id
    WHERE a1.text IS NOT NULL 
      AND a2.text IS NOT NULL 
      AND a1.text != a2.text
      AND (asp1.id IS NULL OR asp2.id IS NULL OR (
          COALESCE(asp1.valid_from, '-infinity'::timestamptz) < COALESCE(asp2.valid_to, 'infinity'::timestamptz)
          AND COALESCE(asp2.valid_from, '-infinity'::timestamptz) < COALESCE(asp1.valid_to, 'infinity'::timestamptz)
      ))
    """
    
    params = {}
    where_clauses = []
    
    if kind is not None:
        where_clauses.append("a1.kind = %(kind)s")
        params["kind"] = kind
    
    if label is not None:
        where_clauses.append("a1.label = %(label)s")
        params["label"] = label
    
    if where_clauses:
        sql += " AND " + " AND ".join(where_clauses)
    
    sql += f" LIMIT {limit}"
    
    contradictions: List[Contradiction] = []
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for row in cur.fetchall():
                (atom1_id, atom1_label, text1, atom2_id, atom2_label, 
                 text2, overlap_start, overlap_end) = row
                
                reason = f"Atoms with same kind+label '{atom1_label}' have different text values: '{text1[:50]}...' vs '{text2[:50]}...'"
                
                contradictions.append(
                    Contradiction(
                        subject_id=atom1_id,
                        subject_label=atom1_label,
                        predicate="text_mismatch",
                        object1_id=atom1_id,
                        object1_label=text1[:100] if text1 else "",
                        object2_id=atom2_id,
                        object2_label=text2[:100] if text2 else "",
                        overlap_start=overlap_start,
                        overlap_end=overlap_end,
                        reason=reason
                    )
                )
    
    return contradictions


def detect_all_contradictions(limit: int = 100) -> List[Contradiction]:
    """
    Detect all types of contradictions.
    
    Args:
        limit: Maximum total contradictions to return
    
    Returns:
        Combined list of all detected contradictions
    """
    fiber_contras = detect_fiber_contradictions(limit=limit)
    remaining = max(0, limit - len(fiber_contras))
    
    if remaining > 0:
        atom_contras = detect_atom_text_contradictions(limit=remaining)
        return fiber_contras + atom_contras
    
    return fiber_contras
