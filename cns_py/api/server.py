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


class GraphEdge(BaseModel):  # type: ignore[misc]
    """Minimal graph edge DTO for Explorer consumption.

    This will eventually surface belief and contradiction flags.
    """

    src_id: int
    dst_id: int
    predicate: str
    confidence: Optional[float] = None


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
    confidence: Optional[float] = None
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

    # When an ASOF instant is provided, prefer the CQL engine as the single
    # source of truth for temporal semantics. We construct a minimal CQL
    # query that asks for outgoing edges from the labeled node at that time
    # and adapt the result into the neighborhood DTO.
    edges_raw: List[tuple[str, str, str]]
    if asof is not None:
        # Use ISO format expected by the CQL executor.
        cql_query = f'MATCH label="{label}" ASOF {asof.isoformat()} RETURN'
        try:
            cql_payload = cql(cql_query)
        except Exception as exc:  # pragma: no cover - defensive; detailed tests elsewhere
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        results = cql_payload.get("results", [])
        edges_raw = [
            (str(item["subject_label"]), str(item["predicate"]), str(item["object_label"]))
            for item in results
        ]
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
        edges_raw = traverse_from(ids, hops=hops, predicates=None, limit=limit)

    # Collect unique labels and resolve them to real CNS atom IDs for Explorer consumption.
    label_set: set[str] = set()
    for subj, _pred, obj in edges_raw:
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
        nodes_all.append(GraphNode(id=atom_id, kind=None, label=lbl))

    edges_all: List[GraphEdge] = []
    for subj_label, pred, obj_label in edges_raw:
        src_id = label_to_id.get(subj_label)
        dst_id = label_to_id.get(obj_label)
        if src_id is None or dst_id is None:
            continue
        edges_all.append(GraphEdge(src_id=src_id, dst_id=dst_id, predicate=pred))

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
                confidence=float(confidence) if confidence is not None else None,
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


# Register routes imperatively to keep decorators out of mypy's way.
app.post("/cql")(run_cql)
app.get("/graph/neighborhood", response_model=GraphNeighborhoodEnvelope)(graph_neighborhood)
app.get("/graph/node/{node_id}", response_model=NodeDetailEnvelope)(graph_node_detail)


def get_app() -> FastAPI:
    """Expose the FastAPI app for ASGI servers/tests."""
    return app
