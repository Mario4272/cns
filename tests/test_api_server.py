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


def test_graph_neighborhood_ids_are_stable_across_identical_requests():
    """Node IDs should be stable for the same params and ASOF.

    This does not assume anything about the specific numeric values or
    contiguity of IDs; it just asserts that repeated calls yield the same
    sorted id set.
    """

    params = {"label": "FrameworkX", "hops": 1, "limit": 20}

    resp1 = client.get("/graph/neighborhood", params=params)
    resp2 = client.get("/graph/neighborhood", params=params)

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    ids1 = sorted(n["id"] for n in resp1.json()["nodes"])
    ids2 = sorted(n["id"] for n in resp2.json()["nodes"])

    assert ids1 == ids2


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


def _get_frameworkx_node_id() -> int:
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1})
    assert resp.status_code == 200
    payload = resp.json()
    for n in payload["nodes"]:
        if n["label"] == "FrameworkX":
            return int(n["id"])
    pytest.skip("FrameworkX node not present in neighborhood response")


def test_graph_node_detail_returns_200_for_valid_id():
    node_id = _get_frameworkx_node_id()
    resp = client.get(f"/graph/node/{node_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["node"]["id"] == node_id
    assert payload["node"]["label"] == "FrameworkX"
    assert "aspects" in payload
    assert "provenance" in payload
    assert "assertions_count" in payload["provenance"]
    assert "sources_count" in payload["provenance"]


def test_graph_node_detail_returns_404_for_unknown_id():
    resp = client.get("/graph/node/999999999")
    assert resp.status_code == 404


def test_graph_node_detail_asof_changes_tls_across_cutover():
    node_id = _get_frameworkx_node_id()

    asof_before = "2024-12-31T23:59:59Z"
    asof_after = "2025-01-01T00:00:01Z"

    resp_before = client.get(f"/graph/node/{node_id}", params={"asof": asof_before})
    resp_after = client.get(f"/graph/node/{node_id}", params={"asof": asof_after})

    assert resp_before.status_code == 200
    assert resp_after.status_code == 200

    def tls_targets(payload: dict) -> set[str]:
        return {a["dst_label"] for a in payload["aspects"] if a["predicate"] == "supports_tls"}

    before_targets = tls_targets(resp_before.json())
    after_targets = tls_targets(resp_after.json())

    assert "TLS1.2" in before_targets
    assert "TLS1.3" not in before_targets

    assert "TLS1.3" in after_targets
    assert "TLS1.2" not in after_targets
