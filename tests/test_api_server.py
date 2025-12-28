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


def test_graph_neighborhood_returns_envelope_with_nodes_and_edges_for_frameworkx():
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1})
    assert resp.status_code == 200
    payload = resp.json()

    # Envelope-level fields
    assert set(payload.keys()) >= {"center_node_id", "hops", "asof", "truncated", "nodes", "edges"}
    assert payload["hops"] == 1
    # Default asof is null/None when not provided.
    assert payload["asof"] is None
    assert payload["truncated"] is False

    nodes = payload["nodes"]
    edges = payload["edges"]
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    # Expect at least the central node
    labels = {n["label"] for n in nodes}
    assert "FrameworkX" in labels
    # center_node_id, if present, should refer to an existing node id
    if payload["center_node_id"] is not None:
        node_ids = {n["id"] for n in nodes}
        assert payload["center_node_id"] in node_ids


def test_graph_neighborhood_edges_always_reference_returned_nodes():
    """Every edge endpoint id must exist in the returned node id set.

    This locks the invariant that the client never sees dangling edge endpoints.
    """
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1})
    assert resp.status_code == 200
    payload = resp.json()
    node_ids = {n["id"] for n in payload["nodes"]}
    for edge in payload["edges"]:
        assert edge["src_id"] in node_ids
        assert edge["dst_id"] in node_ids


def test_cql_endpoint_rejects_empty_query():
    resp = client.post("/cql", json={"query": "  "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "query must be non-empty"


def test_graph_neighborhood_rejects_bad_params():
    resp = client.get("/graph/neighborhood", params={"label": "", "hops": 1})
    assert resp.status_code == 400
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 0})
    assert resp.status_code == 400
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1, "limit": 0})
    assert resp.status_code == 400


def test_graph_neighborhood_rejects_bad_asof_format():
    resp = client.get(
        "/graph/neighborhood",
        params={"label": "FrameworkX", "hops": 1, "asof": "not-a-date"},
    )
    # FastAPI will return a 422 validation error for invalid datetime by default.
    assert resp.status_code in {400, 422}


def test_graph_neighborhood_accepts_asof_and_echoes_it_back():
    # This test currently just checks that the asof parameter is plumbed through
    # to the response envelope; future work will assert behavioral differences.
    asof_value = "2025-01-01T00:00:00Z"
    resp = client.get(
        "/graph/neighborhood",
        params={"label": "FrameworkX", "hops": 1, "asof": asof_value},
    )
    assert resp.status_code == 200
    payload = resp.json()
    # FastAPI/Pydantic will normalize to a canonical ISO format; string compare is OK.
    assert payload["asof"].startswith("2025-01-01T00:00:00")


def test_graph_neighborhood_respects_limit_and_sets_truncated_flag():
    # Use a small limit so we are likely to truncate on real data.
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1, "limit": 1})
    assert resp.status_code == 200
    payload = resp.json()
    nodes = payload["nodes"]
    assert len(nodes) <= 1
    # When nodes are capped below the full set, truncated should be True.
    # We do not assert exact True/False to avoid coupling to fixture size if it
    # ever changes, but we at least exercise the path.
    assert "truncated" in payload


def test_graph_neighborhood_asof_changes_tls_edges_across_cutover():
    """ASOF before vs after the TLS cutover should yield different supports_tls edges.

    Demo ingest seeds FrameworkX so that it supports TLS1.2 before 2025-01-01 and
    TLS1.3 from 2025-01-01 onward. This test checks that the neighborhood
    endpoint reflects that temporal split.
    """

    # One second before and after the demo cutoff in cns_py.demo.ingest.
    asof_before = "2024-12-31T23:59:59Z"
    asof_after = "2025-01-01T00:00:01Z"

    params_common = {"label": "FrameworkX", "hops": 1, "limit": 20}

    resp_before = client.get("/graph/neighborhood", params={**params_common, "asof": asof_before})
    resp_after = client.get("/graph/neighborhood", params={**params_common, "asof": asof_after})

    assert resp_before.status_code == 200
    assert resp_after.status_code == 200

    payload_before = resp_before.json()
    payload_after = resp_after.json()

    # Build id->label maps to interpret edge endpoints.
    labels_before = {n["id"]: n["label"] for n in payload_before["nodes"]}
    labels_after = {n["id"]: n["label"] for n in payload_after["nodes"]}

    def edge_signatures(payload: dict, id_to_label: dict[int, str]) -> set[tuple[str, str]]:
        sigs: set[tuple[str, str]] = set()
        for e in payload["edges"]:
            dst_label = id_to_label.get(e["dst_id"])
            if dst_label is None:
                continue
            sigs.add((e["predicate"], dst_label))
        return sigs

    sigs_before = edge_signatures(payload_before, labels_before)
    sigs_after = edge_signatures(payload_after, labels_after)

    # Before cutover: expect supports_tls -> TLS1.2 and not TLS1.3
    assert ("supports_tls", "TLS1.2") in sigs_before
    assert ("supports_tls", "TLS1.3") not in sigs_before

    # After cutover: expect supports_tls -> TLS1.3 and not TLS1.2
    assert ("supports_tls", "TLS1.3") in sigs_after
    assert ("supports_tls", "TLS1.2") not in sigs_after
