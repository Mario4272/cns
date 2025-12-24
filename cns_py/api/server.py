from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cns_py.cql.executor import cql
from cns_py.graph import traverse_from
from cns_py.nn import nn_search


class CqlRequest(BaseModel):  # type: ignore[misc]
    query: str


class GraphNode(BaseModel):  # type: ignore[misc]
    id: int
    label: str
    kind: Optional[str] = None


class GraphEdge(BaseModel):  # type: ignore[misc]
    src_id: int
    dst_id: int
    predicate: str
    confidence: Optional[float] = None


class GraphNeighborhoodResponse(BaseModel):  # type: ignore[misc]
    nodes: List[GraphNode]
    edges: List[GraphEdge]


app = FastAPI(title="CNS API", version="0.1")


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


def graph_neighborhood(label: str, hops: int = 1, limit: int = 100) -> GraphNeighborhoodResponse:
    """Return a small graph neighborhood for a given atom label.

    This is intended as a backend feed for the IB Explorer galaxy view.
    It currently focuses on outgoing edges from the nearest neighbors of the
    provided label, limited to a small hop count.
    """
    if not label:
        raise HTTPException(status_code=400, detail="label must be non-empty")
    if hops < 1:
        raise HTTPException(status_code=400, detail="hops must be >= 1")

    ids = nn_search(label, k=limit)
    if not ids:
        return GraphNeighborhoodResponse(nodes=[], edges=[])

    # traverse_from returns (src_label, predicate, dst_label)
    edges_raw = traverse_from(ids, hops=hops, predicates=None, limit=limit)

    # Collect unique labels and assign synthetic integer IDs for Explorer consumption.
    label_set: set[str] = set()
    for subj, _pred, obj in edges_raw:
        label_set.add(subj)
        label_set.add(obj)
    # Ensure central label is present even if it has no outbound edges.
    label_set.add(label)

    nodes: List[GraphNode] = []
    label_to_id: Dict[str, int] = {}
    for idx, lbl in enumerate(sorted(label_set)):
        node_id = idx + 1
        label_to_id[lbl] = node_id
        nodes.append(GraphNode(id=node_id, kind=None, label=lbl))
    graph_edges: List[GraphEdge] = []
    for subj_label, pred, obj_label in edges_raw:
        src_id = label_to_id.get(subj_label)
        dst_id = label_to_id.get(obj_label)
        if src_id is None or dst_id is None:
            continue
        graph_edges.append(GraphEdge(src_id=src_id, dst_id=dst_id, predicate=pred))

    return GraphNeighborhoodResponse(nodes=nodes, edges=graph_edges)


# Register routes imperatively to keep decorators out of mypy's way.
app.post("/cql")(run_cql)
app.get("/graph/neighborhood", response_model=GraphNeighborhoodResponse)(graph_neighborhood)


def get_app() -> FastAPI:
    """Expose the FastAPI app for ASGI servers/tests."""
    return app
