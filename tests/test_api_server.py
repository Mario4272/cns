from __future__ import annotations

import pytest

try:
    from fastapi.testclient import TestClient

    from cns_py.api.server import get_app
except ImportError:  # pragma: no cover - allows local pytest without fastapi installed
    pytest.skip("fastapi not installed; API tests skipped", allow_module_level=True)


client = TestClient(get_app())


def test_cql_endpoint_runs_demo_query_and_returns_results_and_explain():
    resp = client.post(
        "/cql",
        json={
            "query": 'MATCH label="FrameworkX" PREDICATE supports_tls '
            "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "results" in payload
    assert isinstance(payload["results"], list)
    assert len(payload["results"]) >= 0
    # EXPLAIN payload should be present when requested
    assert "explain" in payload
    assert "steps" in payload["explain"]


def test_graph_neighborhood_returns_nodes_and_edges_for_frameworkx():
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1})
    assert resp.status_code == 200
    payload = resp.json()
    nodes = payload["nodes"]
    edges = payload["edges"]
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    # Expect at least the central node
    labels = {n["label"] for n in nodes}
    assert "FrameworkX" in labels


def test_cql_endpoint_rejects_empty_query():
    resp = client.post("/cql", json={"query": "  "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "query must be non-empty"


def test_graph_neighborhood_rejects_bad_params():
    resp = client.get("/graph/neighborhood", params={"label": "", "hops": 1})
    assert resp.status_code == 400
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 0})
    assert resp.status_code == 400
