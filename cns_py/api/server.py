from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cns_py import config as cns_config
from cns_py.cql.executor import cql
from cns_py.graph import traverse_from
from cns_py.nn import nn_search
from cns_py.storage.db import get_conn


class CqlRequest(BaseModel):  # type: ignore[misc]
    query: str


class GraphNode(BaseModel):  # type: ignore[misc]
    """Minimal graph node DTO for Explorer consumption.

    This will be extended over time with belief/temporal/provenance fields, but for
    now it carries a stable atom id, a label, and an optional kind.
    """

    id: int
    label: str
    kind: Optional[str] = None
    belief: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None


class GraphEdge(BaseModel):  # type: ignore[misc]
    """Minimal graph edge DTO for Explorer consumption.

    This will eventually surface belief and contradiction flags.
    """

    id: int
    src_id: int
    dst_id: int
    predicate: str
    belief: Optional[float] = None
    provenance: Optional[NodeProvenanceSummary] = None
    contradictions: Optional[List[int]] = None


class GraphNeighborhoodEnvelope(BaseModel):  # type: ignore[misc]
    """Envelope for /graph/neighborhood responses.

    Provides a stable wrapper the Explorer can rely on while we evolve the
    internal graph representation. Additional fields (belief, tape, provenance)
    can be added later without breaking the top-level shape.
    """

    center_node_id: Optional[int]
    hops: int
    asof: Optional[datetime] = None
    truncated: bool
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class NodeAspect(BaseModel):  # type: ignore[misc]
    predicate: str
    dst_id: int
    dst_label: str
    belief: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class NodeProvenanceSummary(BaseModel):  # type: ignore[misc]
    assertions_count: int
    sources_count: int


class NodeDetailEnvelope(BaseModel):  # type: ignore[misc]
    node: GraphNode
    asof: Optional[datetime] = None
    aspects: List[NodeAspect]
    provenance: NodeProvenanceSummary


app = FastAPI(title="CNS API", version="0.1")

# Allow local Explorer (file:// origin) and other dev tools to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_cql(req: CqlRequest) -> Dict[str, Any]:
    """Execute a CQL query and return the raw executor payload.

    This is a thin wrapper over cns_py.cql.executor.cql.
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must be non-empty")
    try:
        return cql(query)
    except Exception as exc:  # pragma: no cover - defensive; detailed tests elsewhere
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def graph_neighborhood(
    label: str,
    hops: int = 1,
    limit: int = 100,
    asof: Optional[datetime] = None,
    policy: str = "all",
) -> GraphNeighborhoodEnvelope:
    """Return a small graph neighborhood for a given atom label.

    This is intended as a backend feed for the IB Explorer galaxy view.
    It currently focuses on outgoing edges from the nearest neighbors of the
    provided label, limited to a small hop count.
    """
    if not label:
        raise HTTPException(status_code=400, detail="label must be non-empty")
    if hops < 1:
        raise HTTPException(status_code=400, detail="hops must be >= 1")
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")

    policy_normalized = policy.lower().strip()
    allowed_policies = {"all", "latest", "highest_confidence"}
    if policy_normalized not in allowed_policies:
        raise HTTPException(status_code=400, detail="invalid policy")

    # When an ASOF instant is provided, prefer the CQL engine as the single
    # source of truth for temporal semantics. We construct a minimal CQL
    # query that asks for outgoing edges from the labeled node at that time
    # and adapt the result into the neighborhood DTO.
    # subject_label, predicate, object_label, confidence, fiber_id, observed_at_iso, provenance_json
    edges_raw: List[
        tuple[
            str,
            str,
            str,
            Optional[float],
            Optional[int],
            Optional[str],
            Optional[Dict[str, Any]],
        ]
    ]
    if asof is not None:
        # Use ISO format expected by the CQL executor.
        cql_query = f'MATCH label="{label}" ASOF {asof.isoformat()} RETURN'
        try:
            cql_payload = cql(cql_query)
        except Exception as exc:  # pragma: no cover - defensive; detailed tests elsewhere
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        results = cql_payload.get("results", [])
        edges_raw = []
        for item in results:
            subj = str(item.get("subject_label"))
            pred = str(item.get("predicate"))
            obj = str(item.get("object_label"))
            conf = item.get("confidence")
            try:
                conf_f = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                conf_f = None
            fiber_id = item.get("fiber_id")
            try:
                fiber_id_i = int(fiber_id) if fiber_id is not None else None
            except (TypeError, ValueError):
                fiber_id_i = None
            observed_at_iso = item.get("observed_at")
            observed_at_iso = item.get("observed_at")
            prov = item.get("provenance_json")
            edges_raw.append((subj, pred, obj, conf_f, fiber_id_i, observed_at_iso, prov))
    else:
        ids = nn_search(label, k=limit)
        if not ids:
            return GraphNeighborhoodEnvelope(
                center_node_id=None,
                hops=hops,
                asof=asof,
                truncated=False,
                nodes=[],
                edges=[],
            )

        # traverse_from returns (src_label, predicate, dst_label)
        edges_simple = traverse_from(ids, hops=hops, predicates=None, limit=limit)
        edges_raw = [(subj, pred, obj, None, None, None, None) for subj, pred, obj in edges_simple]

    # Collect unique labels and resolve them to real CNS atom IDs for Explorer consumption.
    label_set: set[str] = set()
    for subj, _pred, obj, _conf, _fid, _obs, _prov in edges_raw:
        label_set.add(subj)
        label_set.add(obj)
    # Ensure central label is present even if it has no outbound edges.
    label_set.add(label)

    label_to_id: Dict[str, int] = {}
    if label_set:
        labels_list = sorted(label_set)
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Use the smallest atom id per label to keep things stable but simple.
                cur.execute(
                    (
                        "SELECT label, id "
                        "FROM atoms "
                        "WHERE label = ANY(%(labels)s::text[]) "
                        "ORDER BY label, id"
                    ),
                    {"labels": labels_list},
                )
                for lbl, atom_id in cur.fetchall():
                    if lbl not in label_to_id:
                        try:
                            label_to_id[str(lbl)] = int(atom_id)
                        except Exception:
                            continue

    nodes_all: List[GraphNode] = []
    for lbl, atom_id in label_to_id.items():
        nodes_all.append(
            GraphNode(
                id=atom_id,
                kind=None,
                label=lbl,
                belief=1.0,  # Atoms are logically true if they exist; refinement later.
                x=None,
                y=None,
                z=None,
            )
        )

    edges_all: List[GraphEdge] = []
    for subj_label, pred, obj_label, conf, fiber_id, observed_at_iso, prov_json in edges_raw:
        src_id = label_to_id.get(subj_label)
        dst_id = label_to_id.get(obj_label)
        if src_id is None or dst_id is None:
            continue

        edge_id = fiber_id if fiber_id is not None else abs(hash((src_id, dst_id, pred)))

        # Provenance Summary
        assertions_count = 1 if prov_json is not None else 0
        sources_count = 0
        if isinstance(prov_json, dict):
            src_field = prov_json.get("source_id")
            if src_field is not None:
                sources_count = 1  # Simplified for now; schema allows richer prov later

        prov_summary = NodeProvenanceSummary(
            assertions_count=assertions_count,
            sources_count=sources_count,
        )

        edges_all.append(
            GraphEdge(
                id=int(edge_id),
                src_id=src_id,
                dst_id=dst_id,
                predicate=pred,
                belief=conf,
                provenance=prov_summary,
            )
        )

    # Compute contradictions (same src, same pred, different dst)
    # We do not have a separate list of contradictions in the raw results, but we can
    # infer them within the retrieved window. This is a "best effort" contradiction list based
    # on the neighborhood view.
    grouped_by_key: Dict[tuple[int, str], List[GraphEdge]] = {}
    for e in edges_all:
        grouped_by_key.setdefault((e.src_id, e.predicate), []).append(e)

    for e in edges_all:
        group = grouped_by_key[(e.src_id, e.predicate)]
        # Contradictions are other edges in the same group with DIFFERENT dst
        conflicts = [other.id for other in group if other.dst_id != e.dst_id]
        if conflicts:
            e.contradictions = conflicts

    # Apply truth policy at the slot level when we have real fiber-backed
    # edges (ASOF/CQL path). The ANN path may synthesize ids but cannot
    # compute effective_time, so policy=all is effectively a no-op there.
    if policy_normalized != "all" and asof is not None:
        from datetime import timezone

        def _effective_time(edge: GraphEdge) -> datetime:
            if edge.belief is None and asof is not None:
                return asof
            # We do not currently surface observed_at at the neighborhood
            # level; fall back to ASOF for deterministic ordering.
            return asof or datetime.min.replace(tzinfo=timezone.utc)

        keyed: Dict[tuple[int, str], List[GraphEdge]] = {}
        for e in edges_all:
            key = (e.src_id, e.predicate)
            keyed.setdefault(key, []).append(e)

        selected: List[GraphEdge] = []
        for (_src, _pred), group in keyed.items():

            def sort_key(edge: GraphEdge) -> tuple[float, float, int, int]:
                conf_val = 0.0 if edge.belief is None else float(edge.belief)
                eff_time = _effective_time(edge)
                if policy_normalized == "latest":
                    return (-eff_time.timestamp(), -conf_val, edge.dst_id, edge.id)
                # highest_confidence
                return (-conf_val, -eff_time.timestamp(), edge.dst_id, edge.id)

            winner = sorted(group, key=sort_key)[0]
            selected.append(winner)
        edges_all = selected

    # Determine whether we need to truncate. We cap nodes to `limit`; edges are
    # then filtered to only those whose endpoints are present.
    truncated = len(nodes_all) > limit
    nodes_capped = sorted(nodes_all, key=lambda n: n.id)[:limit]
    allowed_ids = {n.id for n in nodes_capped}
    edges_capped = [e for e in edges_all if e.src_id in allowed_ids and e.dst_id in allowed_ids]

    center_node_id = None
    if label in label_to_id:
        center_candidate = label_to_id[label]
        if center_candidate in allowed_ids:
            center_node_id = center_candidate

    return GraphNeighborhoodEnvelope(
        center_node_id=center_node_id,
        hops=hops,
        asof=asof,
        truncated=truncated,
        nodes=nodes_capped,
        edges=edges_capped,
    )


class EdgeReceipt(BaseModel):  # type: ignore[misc]
    id: int
    src_id: int
    dst_id: int
    predicate: str
    belief: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    observed_at: Optional[datetime] = None


class EdgeReceiptEnvelope(BaseModel):  # type: ignore[misc]
    edge: EdgeReceipt
    src_label: Optional[str]
    dst_label: Optional[str]
    provenance: NodeProvenanceSummary
    contradictions: List[int]


def graph_edge_detail(edge_id: int, asof: Optional[datetime] = None) -> EdgeReceiptEnvelope:
    if edge_id <= 0:
        raise HTTPException(status_code=400, detail="id must be positive")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Load edge + aspect
            base_sql = (
                "SELECT f.id, f.src, f.dst, f.predicate, "
                "asp.belief AS confidence, asp.valid_from, asp.valid_to, asp.observed_at, "
                "a_src.label AS src_label, a_dst.label AS dst_label, asp.provenance "
                "FROM fibers f "
                "JOIN atoms a_src ON a_src.id = f.src "
                "JOIN atoms a_dst ON a_dst.id = f.dst "
                "LEFT JOIN aspects asp ON asp.subject_kind='fiber' AND asp.subject_id=f.id "
            )

            where_clauses: List[str] = ["f.id = %(edge_id)s"]
            params: Dict[str, Any] = {"edge_id": edge_id}

            if asof is not None:
                where_clauses.append(
                    "COALESCE(asp.valid_from, '-infinity'::timestamptz) <= %(ts_from)s"
                )
                params["ts_from"] = asof
                end_pred = cns_config.temporal_predicate()
                where_clauses.append(end_pred)
                params["ts_to"] = asof

            sql = base_sql + "WHERE " + " AND ".join(where_clauses) + " LIMIT 1"
            cur.execute(sql, params)
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="edge not found")

            (
                f_id,
                src_id,
                dst_id,
                predicate,
                confidence,
                valid_from,
                valid_to,
                observed_at,
                src_label,
                dst_label,
                prov_json,
            ) = row

            edge = EdgeReceipt(
                id=int(f_id),
                src_id=int(src_id),
                dst_id=int(dst_id),
                predicate=str(predicate),
                belief=float(confidence) if confidence is not None else None,
                valid_from=valid_from,
                valid_to=valid_to,
                observed_at=observed_at,
            )

            assertions_count = 1 if prov_json is not None else 0
            sources: set[str] = set()
            if isinstance(prov_json, dict):
                src_field = prov_json.get("source_id")
                if src_field is not None:
                    sources.add(str(src_field))

            provenance = NodeProvenanceSummary(
                assertions_count=assertions_count,
                sources_count=len(sources),
            )

            # For now, compute contradictions cheaply by looking for competing
            # fibers with the same (src, predicate) but different dst under the
            # same ASOF mask. This reuses the temporal predicate from config.
            contradictions: List[int] = []
            contra_sql = (
                "SELECT f2.id FROM fibers f2 "
                "LEFT JOIN aspects asp2 ON asp2.subject_kind='fiber' AND asp2.subject_id=f2.id "
                "WHERE f2.src = %(src_id)s AND f2.predicate = %(predicate)s "
                "AND f2.dst <> %(dst_id)s"
            )
            contra_params: Dict[str, Any] = {
                "src_id": src_id,
                "dst_id": dst_id,
                "predicate": predicate,
            }
            if asof is not None:
                contra_sql += (
                    " AND COALESCE(asp2.valid_from, '-infinity'::timestamptz) <= %(ts_from)s"
                )
                contra_params["ts_from"] = asof
                end_pred2 = cns_config.temporal_predicate().replace("asp.", "asp2.")
                contra_sql += " AND " + end_pred2
                contra_params["ts_to"] = asof

            cur.execute(contra_sql, contra_params)
            for (other_id,) in cur.fetchall():
                try:
                    contradictions.append(int(other_id))
                except Exception:
                    continue

    return EdgeReceiptEnvelope(
        edge=edge,
        src_label=str(src_label) if src_label is not None else None,
        dst_label=str(dst_label) if dst_label is not None else None,
        provenance=provenance,
        contradictions=contradictions,
    )


def graph_node_detail(node_id: int, asof: Optional[datetime] = None) -> NodeDetailEnvelope:
    """Return a minimal detail view for a single node.

    This endpoint exposes a receipts-lite view: basic node identity, a capped
    list of outgoing aspects, and a coarse provenance summary. ASOF applies the
    same temporal semantics as the CQL executor.
    """

    if node_id <= 0:
        raise HTTPException(status_code=400, detail="id must be positive")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, label, kind FROM atoms WHERE id = %(id)s",
                {"id": node_id},
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="node not found")
            atom_id, label, kind = row
            node = GraphNode(id=int(atom_id), label=str(label), kind=kind)

            base_sql = (
                "SELECT f.predicate, a_dst.id AS dst_id, a_dst.label AS dst_label, "
                "asp.belief AS confidence, asp.valid_from, asp.valid_to, asp.provenance "
                "FROM fibers f "
                "JOIN atoms a_dst ON a_dst.id = f.dst "
                "LEFT JOIN aspects asp ON asp.subject_kind='fiber' AND asp.subject_id=f.id "
            )

            where_clauses: List[str] = ["f.src = %(node_id)s"]
            params: Dict[str, Any] = {"node_id": node_id}

            if asof is not None:
                ts_from = asof
                ts_to = asof
                where_clauses.append(
                    "COALESCE(asp.valid_from, '-infinity'::timestamptz) <= %(ts_from)s"
                )
                params["ts_from"] = ts_from
                end_pred = cns_config.temporal_predicate()
                where_clauses.append(end_pred)
                params["ts_to"] = ts_to

            sql = base_sql + "WHERE " + " AND ".join(where_clauses) + " "
            sql += "ORDER BY f.predicate, a_dst.label LIMIT 200"

            cur.execute(sql, params)
            rows = cur.fetchall()

    aspects: List[NodeAspect] = []
    assertions_count = 0
    source_ids: set[str] = set()

    for (
        predicate,
        dst_id,
        dst_label,
        confidence,
        valid_from,
        valid_to,
        prov_json,
    ) in rows:
        aspects.append(
            NodeAspect(
                predicate=str(predicate),
                dst_id=int(dst_id),
                dst_label=str(dst_label),
                belief=float(confidence) if confidence is not None else None,
                valid_from=valid_from,
                valid_to=valid_to,
            )
        )
        assertions_count += 1

        if isinstance(prov_json, dict):
            src_id = prov_json.get("source_id")
            if src_id is not None:
                source_ids.add(str(src_id))

    provenance_summary = NodeProvenanceSummary(
        assertions_count=assertions_count,
        sources_count=len(source_ids),
    )

    return NodeDetailEnvelope(
        node=node,
        asof=asof,
        aspects=aspects,
        provenance=provenance_summary,
    )


# ... existing code ...


import os

from cns_py.vector.manager import IndexManager

# Initialize Vector Index Manager (Singleton)
_INDEX_MANAGER = IndexManager()

@app.on_event("startup")
def startup_event() -> None:
    """Initialize resources on startup."""
    # This handles loading persistence or rebuilding if needed
    _INDEX_MANAGER.startup()

@app.on_event("shutdown")
def shutdown_event() -> None:
    """Cleanup resources on shutdown."""
    _INDEX_MANAGER.shutdown()


class VectorQuery(BaseModel):
    vector: List[float]
    k: int = 10
    filter: Optional[Dict[str, Any]] = None


class SimilarResult(BaseModel):
    id: str
    score: float
    # Slice 4: Add explicit fields for easier consumption
    label: Optional[str] = None
    kind: Optional[str] = None


class SimilarNodesEnvelope(BaseModel):
    results: List[SimilarResult]


def find_similar(req: VectorQuery) -> SimilarNodesEnvelope:
    """Find similar items by vector.
    Delegates to IndexManager.
    """
    try:
        # IndexManager.query returns List[ScoredResult] i.e. (id, score)
        # But we want to enrich this eventually. For now, we return what we have.
        # The Manager query is just a proxy to the index.
        # To get label/kind, we might need to fetch from DB or store in metadata.
        # Slice 4 requirement: "Response should include... label... kind"
        # Since we stored metadata in IndexManager.rebuild(), we can retrieve it if the Index supports it.
        # But VectorIndex.query only returns (id, score).
        # We need to fetch details. Or checking if IndexManager can return metadata.
        
        # Let's see... ExactInMemoryIndex stores metadata.
        # But query() interface returns ScoredResult (id, score).
        # We should probably fetch atoms from DB to be Safe and Real.
        # OR extend query interface? Contract says: return List[ScoredResult].
        
        raw_results = _INDEX_MANAGER.query(req.vector, k=req.k, filter=req.filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Enrich results with Label/Kind from DB (or cache if we had one)
    # Since we need "Real Index Lifecycle", fetching from DB ensures freshness.
    results = []
    if raw_results:
        ids = [r[0] for r in raw_results]
        # Bulk fetch details
        atom_details = {}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, label, kind FROM atoms WHERE id::text = ANY(%(ids)s::text[])", # ID is text in Index
                     # But DB id is int? Wait. 
                     # IndexManager.rebuild stored str(atom_id_int).
                     # So we cast back.
                    {"ids": ids}
                )
                for row in cur.fetchall():
                    atom_id, label, kind = row
                    atom_details[str(atom_id)] = (label, kind)

        for doc_id, score in raw_results:
            label, kind = atom_details.get(doc_id, (None, None))
            results.append(SimilarResult(id=doc_id, score=score, label=label, kind=kind))

    return SimilarNodesEnvelope(results=results)


# Register routes imperatively to keep decorators out of mypy's way.
app.post("/cql")(run_cql)
app.get("/graph/neighborhood", response_model=GraphNeighborhoodEnvelope)(graph_neighborhood)
app.get("/graph/node/{node_id}", response_model=NodeDetailEnvelope)(graph_node_detail)
app.get("/graph/edge/{edge_id}", response_model=EdgeReceiptEnvelope)(graph_edge_detail)
app.post("/graph/similar", response_model=SimilarNodesEnvelope)(find_similar)


def get_app() -> FastAPI:
    """Expose the FastAPI app for ASGI servers/tests."""
    return app

