from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cns_py.cql.executor import cql
from cns_py.graph import traverse_from
from cns_py.nn import nn_search


class CqlRequest(BaseModel):  # type: ignore[misc]
    query: str


class GraphNode(BaseModel):  # type: ignore[misc]
    """Minimal graph node DTO for Explorer consumption.

    This will be extended over time with belief/temporal/provenance fields, but for
    now it carries a synthetic integer id, a label, and an optional kind.
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

    # Collect unique labels and assign synthetic integer IDs for Explorer consumption.
    label_set: set[str] = set()
    for subj, _pred, obj in edges_raw:
        label_set.add(subj)
        label_set.add(obj)
    # Ensure central label is present even if it has no outbound edges.
    label_set.add(label)

    nodes_all: List[GraphNode] = []
    label_to_id: Dict[str, int] = {}
    for idx, lbl in enumerate(sorted(label_set)):
        node_id = idx + 1
        label_to_id[lbl] = node_id
        nodes_all.append(GraphNode(id=node_id, kind=None, label=lbl))

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


# Register routes imperatively to keep decorators out of mypy's way.
app.post("/cql")(run_cql)
app.get("/graph/neighborhood", response_model=GraphNeighborhoodEnvelope)(graph_neighborhood)


def get_app() -> FastAPI:
    """Expose the FastAPI app for ASGI servers/tests."""
    return app
