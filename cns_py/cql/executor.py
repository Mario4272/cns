from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dateutil.parser import isoparse

from cns_py import config as cns_config
from cns_py.storage.db import get_conn

from .belief import compute as belief_compute
from .parser import CqlQuery
from .types import ExplainReport, ExplainStep, Provenance, ResultItem


def _asof_bounds(asof_iso: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    if not asof_iso:
        return None, None
    ts = isoparse(asof_iso)
    return ts, ts


def execute(q: CqlQuery) -> Dict[str, Any]:
    steps: List[ExplainStep] = []
    t0 = time.perf_counter()

    # Planner step (simple heuristic estimates for now)
    plan_extra: Dict[str, Any] = {}
    if q.label:
        plan_extra["label"] = q.label
    if q.predicate:
        plan_extra["predicate"] = q.predicate
    if q.asof_iso:
        plan_extra["asof"] = q.asof_iso
    if q.belief_ge is not None:
        plan_extra["belief_ge"] = q.belief_ge
    # naive estimates
    plan_extra["est_base"] = 1 if q.label else 10
    plan_extra["est_fanout"] = 2 if q.predicate else 5
    steps.append(ExplainStep(name="planner", ms=0.0, extra=plan_extra))

    # Step 1: ANN shortlist (placeholder for Phase 1; 0ms)
    t_ann0 = time.perf_counter()
    # shortlist_ids: Optional[List[int]] = None  # Future: vector shortlist
    t_ann1 = time.perf_counter()
    steps.append(ExplainStep(name="ann_shortlist", ms=(t_ann1 - t_ann0) * 1000.0, extra={}))

    # Step 2: temporal mask bounds
    t_mask0 = time.perf_counter()
    ts_from, ts_to = _asof_bounds(q.asof_iso)
    t_mask1 = time.perf_counter()
    steps.append(
        ExplainStep(
            name="temporal_mask", ms=(t_mask1 - t_mask0) * 1000.0, extra={"asof": q.asof_iso}
        )
    )

    # Step 3: graph traverse and filters
    t_trav0 = time.perf_counter()
    base_select = (
        "SELECT a_src.label AS subject_label, "
        "f.predicate AS predicate, "
        "a_dst.label AS object_label, "
        "COALESCE(asp.belief, 0.0) AS base_confidence, "
        "asp.observed_at AS observed_at, "
        "asp.provenance AS provenance_json, "
        "f.id AS fiber_id "
        "FROM fibers f "
        "JOIN atoms a_src ON a_src.id = f.src "
        "JOIN atoms a_dst ON a_dst.id = f.dst "
        "LEFT JOIN aspects asp ON asp.subject_kind='fiber' AND asp.subject_id=f.id "
    )
    where_clauses: list[str] = []
    params: dict[str, object] = {}

    if q.label is not None:
        where_clauses.append("a_src.label = %(label)s")
        params["label"] = q.label
    if q.predicate is not None:
        where_clauses.append("f.predicate = %(predicate)s")
        params["predicate"] = q.predicate
    if ts_from is not None:
        where_clauses.append("COALESCE(asp.valid_from, '-infinity'::timestamptz) <= %(ts_from)s")
        params["ts_from"] = ts_from
        # Configurable end boundary predicate
        end_pred = cns_config.temporal_predicate()
        where_clauses.append(end_pred)
        params["ts_to"] = ts_to
    if q.belief_ge is not None:
        where_clauses.append("COALESCE(asp.belief, 0.0) >= %(belief_ge)s")
        params["belief_ge"] = q.belief_ge

    sql = base_select
    if where_clauses:
        sql += "WHERE " + " AND ".join(where_clauses) + " "
    sql += "ORDER BY COALESCE(asp.belief, 0.0) DESC LIMIT 100"

    results: List[ResultItem] = []
    raw_rows: List[
        Tuple[str, str, str, float, Optional[datetime], Optional[Dict[str, Any]], int]
    ] = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Debug: Test if the query works without temporal filter
            if q.label == "FrameworkX" and q.asof_iso:
                test_sql = (
                    base_select + "WHERE a_src.label = %(label)s AND f.predicate = %(predicate)s"
                )
                test_params = {"label": q.label, "predicate": q.predicate}
                print(f"[CQL DEBUG] Test SQL: {test_sql}")
                print(f"[CQL DEBUG] Test params: {test_params}")
                cur.execute(test_sql, test_params)
                test_rows = cur.fetchall()
                print(f"[CQL DEBUG] Without temporal filter: {len(test_rows)} rows")
                for row in test_rows:
                    print(f"  Row: {row}")

            # Debug: print SQL and params to diagnose empty results
            print(f"[CQL DEBUG] SQL: {sql}")
            print(f"[CQL DEBUG] Params: {params}")
            try:
                cur.execute(sql, params)
            except Exception:
                # Debug output to help diagnose SQL/params issues during early Phase 1
                debug = {
                    "sql": sql,
                    "params": {k: (str(v) if v is not None else None) for k, v in params.items()},
                }
                print("[CQL DEBUG] execute failed:", debug)
                raise
            rows = cur.fetchall()
            print(f"[CQL DEBUG] Rows returned: {len(rows)}")
            for row in rows:
                subj, pred, obj, base_conf, observed_at, prov_json, fiber_id = row
                raw_rows.append(
                    (
                        subj,
                        pred,
                        obj,
                        float(base_conf or 0.0),
                        observed_at,
                        prov_json,
                        int(fiber_id),
                    )
                )

    t_trav1 = time.perf_counter()
    steps.append(
        ExplainStep(
            name="graph_traverse", ms=(t_trav1 - t_trav0) * 1000.0, extra={"rows": len(results)}
        )
    )

    # Belief compute step (aggregate) with timing and citations enforcement
    t_bel0 = time.perf_counter()
    belief_items = 0
    _sum_base = 0.0
    _sum_conf = 0.0
    _sum_rec = 0.0
    belief_terms: Dict[int, Dict[str, Any]] = {}
    for subj, pred, obj, base_conf, observed_at, prov_json, fiber_id in raw_rows:
        # Enforce citations: require provenance JSON dict with at least one informative field
        has_citation = isinstance(prov_json, dict) and (
            bool(prov_json.get("source_id")) or bool(prov_json.get("uri"))
        )
        if not has_citation:
            continue
        conf, details = belief_compute(base_conf, observed_at)
        belief_items += 1
        _sum_base += float(base_conf or 0.0)
        _sum_conf += float(conf)
        _sum_rec += float(details.get("recency", 0.0))
        # record terms breakdown by fiber_id
        belief_terms[fiber_id] = {
            "before": float(base_conf or 0.0),
            "after": float(conf),
            "terms": dict(details),
        }
        prov_dict: Dict[str, Any] = prov_json if isinstance(prov_json, dict) else {}
        prov: List[Provenance] = [
            Provenance(
                source_id=prov_dict.get("source_id") or f"fiber:{fiber_id}",
                uri=prov_dict.get("uri"),
                line_span=prov_dict.get("line_span"),
                fetched_at=prov_dict.get("fetched_at"),
                hash=prov_dict.get("hash"),
            )
        ]
        results.append(
            ResultItem(
                subject_label=subj,
                predicate=pred,
                object_label=obj,
                confidence=conf,
                provenance=prov,
                belief_details=details,
            )
        )
    t_bel1 = time.perf_counter()
    extra: Dict[str, Any] = {"items": belief_items, "belief_terms": belief_terms}
    if belief_items > 0:
        extra.update(
            {
                "avg_base_belief": _sum_base / belief_items,
                "avg_confidence": _sum_conf / belief_items,
                "avg_recency": _sum_rec / belief_items,
            }
        )
    steps.append(ExplainStep(name="belief_compute", ms=(t_bel1 - t_bel0) * 1000.0, extra=extra))

    total_ms = (time.perf_counter() - t0) * 1000.0
    report = ExplainReport(steps=steps, total_ms=total_ms)

    payload: Dict[str, Any] = {
        "results": [
            {
                "subject_label": r.subject_label,
                "predicate": r.predicate,
                "object_label": r.object_label,
                "confidence": r.confidence,
                "provenance": [asdict(p) for p in r.provenance],
            }
            for r in results
        ]
    }
    if q.explain:
        payload["explain"] = {
            "total_ms": report.total_ms,
            "steps": [asdict(s) for s in report.steps],
        }
    return payload


def cql(query: str) -> Dict[str, Any]:
    from .parser import parse

    q = parse(query)
    return execute(q)
