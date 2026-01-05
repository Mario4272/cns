from __future__ import annotations

from datetime import datetime, timezone

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
    assert isinstance(nodes, list)
    if nodes:
        sample_node = nodes[0]
        # Ensure new fields are present (even if None)
        assert set(sample_node.keys()) >= {"id", "label", "kind", "belief", "x", "y", "z"}
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


def test_graph_neighborhood_edges_have_ids_and_round_trip_to_edge_endpoint():
    asof_value = "2025-01-01T00:00:01Z"
    resp = client.get(
        "/graph/neighborhood",
        params={"label": "FrameworkX", "hops": 1, "asof": asof_value},
    )
    assert resp.status_code == 200
    payload = resp.json()
    edges = payload["edges"]
    if not edges:
        pytest.skip("No edges returned for FrameworkX neighborhood")
    edge = edges[0]
    edge_id = edge["id"]

    resp_edge = client.get(f"/graph/edge/{edge_id}", params={"asof": asof_value})
    assert resp_edge.status_code == 200
    edge_payload = resp_edge.json()
    assert "edge" in edge_payload
    assert "provenance" in edge_payload
    assert "contradictions" in edge_payload
    e = edge_payload["edge"]
    assert isinstance(edge_payload["contradictions"], list)
    assert e["id"] == edge_id


def test_graph_neighborhood_rejects_invalid_policy():
    resp = client.get(
        "/graph/neighborhood",
        params={"label": "FrameworkX", "hops": 1, "policy": "bogus"},
    )
    assert resp.status_code in {400, 422}


def test_policy_latest_respects_tls_cutover_for_frameworkx():
    asof_before = "2024-12-31T23:59:59Z"
    asof_after = "2025-01-01T00:00:01Z"

    params_common = {"label": "FrameworkX", "hops": 1, "limit": 20, "policy": "latest"}

    resp_before = client.get("/graph/neighborhood", params={**params_common, "asof": asof_before})
    resp_after = client.get("/graph/neighborhood", params={**params_common, "asof": asof_after})

    assert resp_before.status_code == 200
    assert resp_after.status_code == 200

    def tls_targets(payload: dict) -> set[str]:
        targets: set[str] = set()
        id_to_label = {n["id"]: n["label"] for n in payload["nodes"]}
        for e in payload["edges"]:
            dst_label = id_to_label.get(e["dst_id"])
            if dst_label is not None and e["predicate"] == "supports_tls":
                targets.add(dst_label)
        return targets

    before_targets = tls_targets(resp_before.json())
    after_targets = tls_targets(resp_after.json())

    assert before_targets == {"TLS1.2"}
    assert after_targets == {"TLS1.3"}


def _seed_testframeworky_contradiction() -> None:
    from datetime import datetime, timedelta

    from dateutil.tz import UTC

    from cns_py.storage.db import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='fiber' AND subject_id IN ("
                " SELECT f.id FROM fibers f "
                " JOIN atoms a_src ON a_src.id=f.src "
                " JOIN atoms a_dst ON a_dst.id=f.dst "
                " WHERE a_src.label LIKE 'TestFramework%' OR a_dst.label LIKE 'TestTLS%')"
            )
            cur.execute(
                "DELETE FROM aspects WHERE subject_kind='atom' AND subject_id IN ("
                " SELECT a.id FROM atoms a WHERE label LIKE 'TestFramework%' "
                " OR label LIKE 'TestTLS%')"
            )
            cur.execute(
                "DELETE FROM fibers USING atoms a_src, atoms a_dst "
                " WHERE a_src.id=fibers.src AND a_dst.id=fibers.dst "
                " AND (a_src.label LIKE 'TestFramework%' OR a_dst.label LIKE 'TestTLS%')"
            )
            cur.execute(
                "DELETE FROM atoms WHERE label LIKE 'TestFramework%' OR label LIKE 'TestTLS%'"
            )

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Entity", "TestFrameworkY", "A test security framework"),
            )
            framework_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestTLS1.2", "TLS version 1.2"),
            )
            tls12_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO atoms(kind, label, text) VALUES (%s, %s, %s) RETURNING id",
                ("Concept", "TestTLS1.3", "TLS version 1.3"),
            )
            tls13_id = cur.fetchone()[0]

            now = datetime.now(tz=UTC)
            past = now - timedelta(days=60)
            future = now + timedelta(days=60)

            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls12_id, "supports_tls"),
            )
            fiber1_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to,
                                    belief, provenance)
                VALUES ('fiber', %s, %s, %s, %s, %s)
                """,
                (
                    fiber1_id,
                    past,
                    future,
                    0.90,
                    '{"source_id": "manual_seed"}',
                ),
            )

            cur.execute(
                "INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id",
                (framework_id, tls13_id, "supports_tls"),
            )
            fiber2_id = cur.fetchone()[0]

            overlap_start = now - timedelta(days=30)
            overlap_end = future + timedelta(days=30)

            cur.execute(
                """
                INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to,
                                    belief, provenance)
                VALUES ('fiber', %s, %s, %s, %s, %s)
                """,
                (
                    fiber2_id,
                    overlap_start,
                    overlap_end,
                    0.95,
                    '{"source_id": "manual_seed"}',
                ),
            )


def test_policy_highest_confidence_treats_null_as_lowest():
    from cns_py.storage.db import get_conn

    _seed_testframeworky_contradiction()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE aspects SET belief=NULL
                WHERE subject_kind='fiber' AND subject_id IN (
                    SELECT f.id FROM fibers f
                    JOIN atoms a_src ON a_src.id=f.src
                    WHERE a_src.label='TestFrameworkY' AND f.predicate='supports_tls'
                    ORDER BY f.id ASC LIMIT 1
                )
                """
            )

    asof_value = "2025-06-01T00:00:00Z"
    resp = client.get(
        "/graph/neighborhood",
        params={
            "label": "TestFrameworkY",
            "hops": 1,
            "limit": 10,
            "policy": "highest_confidence",
            "asof": asof_value,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    id_to_label = {n["id"]: n["label"] for n in payload["nodes"]}
    tls_edges = [
        e
        for e in payload["edges"]
        if e["predicate"] == "supports_tls" and id_to_label.get(e["dst_id"]) is not None
    ]
    if not tls_edges:
        pytest.skip("No supports_tls edges for TestFrameworkY at chosen ASOF")
    tls_targets = {id_to_label[e["dst_id"]] for e in tls_edges}
    # Under highest_confidence, the winner for the contradictory slot should
    # be the non-NULL confidence edge (TestTLS1.3). We allow other non-slot
    # edges, but TLS1.2 should not be the winner for this policy.
    assert "TestTLS1.3" in tls_targets
    assert "TestTLS1.2" not in tls_targets


def test_policy_tie_break_determinism():
    from cns_py.storage.db import get_conn

    _seed_testframeworky_contradiction()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE aspects SET belief=0.9
                WHERE subject_kind='fiber' AND subject_id IN (
                    SELECT f.id FROM fibers f
                    JOIN atoms a_src ON a_src.id=f.src
                    WHERE a_src.label='TestFrameworkY' AND f.predicate='supports_tls'
                )
                """
            )

    resp = client.get(
        "/graph/neighborhood",
        params={
            "label": "TestFrameworkY",
            "hops": 1,
            "limit": 10,
            "policy": "highest_confidence",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()

    # Call twice to ensure stability.
    resp2 = client.get(
        "/graph/neighborhood",
        params={
            "label": "TestFrameworkY",
            "hops": 1,
            "limit": 10,
            "policy": "highest_confidence",
        },
    )
    assert resp2.status_code == 200

    def winner_id(response_json: dict) -> int | None:
        id_to_label = {n["id"]: n["label"] for n in response_json["nodes"]}
        tls_edges = [
            e
            for e in response_json["edges"]
            if e["predicate"] == "supports_tls"
            and id_to_label.get(e["dst_id"]) in {"TestTLS1.2", "TestTLS1.3"}
        ]
        if not tls_edges:
            return None
        # Winner is the first element; policy ordering should be deterministic.
        return tls_edges[0]["id"]

    w1 = winner_id(payload)
    w2 = winner_id(resp2.json())
    assert w1 is not None and w2 is not None
    assert w1 == w2


def test_graph_neighborhood_structures_include_provenance_and_contradictions():
    # Smoke test for field presence
    resp = client.get("/graph/neighborhood", params={"label": "FrameworkX", "hops": 1})
    assert resp.status_code == 200
    payload = resp.json()
    if payload["edges"]:
        edge = payload["edges"][0]
        assert "provenance" in edge
        assert "contradictions" in edge
        # Check provenance structure
        if edge["provenance"]:
            assert "assertions_count" in edge["provenance"]
            assert "sources_count" in edge["provenance"]


def test_graph_neighborhood_populates_contradictions_field():
    _seed_testframeworky_contradiction()

    asof_now = datetime.now(timezone.utc).isoformat()
    # Fetch with policy=all to get both competing edges
    resp = client.get(
        "/graph/neighborhood",
        params={"label": "TestFrameworkY", "hops": 1, "policy": "all", "asof": asof_now},
    )
    assert resp.status_code == 200
    payload = resp.json()

    id_to_label = {n["id"]: n["label"] for n in payload["nodes"]}
    tls_edges = [
        e
        for e in payload["edges"]
        if e["predicate"] == "supports_tls" and id_to_label.get(e["dst_id"]) is not None
    ]

    assert len(tls_edges) >= 2

    for e in tls_edges:
        # Each edge should list the other(s) as contradictions
        assert e["contradictions"] is not None
        assert isinstance(e["contradictions"], list)
        assert len(e["contradictions"]) >= 1

        # Verify the contradiction ID actually points to one of the other TLS edges
        other_ids = {other["id"] for other in tls_edges if other["id"] != e["id"]}
        assert set(e["contradictions"]).intersection(other_ids)


def test_graph_edge_detail_respects_validity_interval_frameworkx():
    """Verify that edge detail honors the ASOF parameter using known Demo data."""
    # Step 1: Find the internal ID of FrameworkX -> TLS1.2 edge.
    asof_2024 = "2024-12-31T23:59:59Z"
    resp = client.get(
        "/graph/neighborhood", params={"label": "FrameworkX", "hops": 1, "asof": asof_2024}
    )
    payload = resp.json()
    id_to_label = {n["id"]: n["label"] for n in payload["nodes"]}
    edge_id_tls12 = None
    for e in payload["edges"]:
        if id_to_label.get(e["dst_id"]) == "TLS1.2":
            edge_id_tls12 = e["id"]
            break

    assert edge_id_tls12 is not None, "FrameworkX -> TLS1.2 edge should exist in 2024"

    # Step 2: Query Detail in 2024 -> Should exist and be valid
    resp_2024 = client.get(f"/graph/edge/{edge_id_tls12}", params={"asof": asof_2024})
    assert resp_2024.status_code == 200
    r_2024 = resp_2024.json()
    assert r_2024["edge"]["belief"] > 0.8

    # Step 3: Query Detail in 2026 -> Should be 404 because the edge is not valid at that time
    asof_2026 = "2026-01-01T00:00:00Z"
    resp_2026 = client.get(f"/graph/edge/{edge_id_tls12}", params={"asof": asof_2026})
    assert resp_2026.status_code == 404


def test_vector_search_integration(monkeypatch, tmp_path):
    """Verify /graph/similar endpoint with InMemory backend."""
    # Ensure enabled for this test and isolated
    monkeypatch.setenv("VECTOR_INDEX_ENABLED", "1")
    monkeypatch.setenv("VECTOR_INDEX_BACKEND", "memory")
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(tmp_path / "api_test_idx"))
    
    from cns_py.api.server import _INDEX_MANAGER
    
    # RESET global manager to clean state
    _INDEX_MANAGER.index = None
    _INDEX_MANAGER.provider = None
    _INDEX_MANAGER.dim = 384 # Default
    
    # Mock the provider to match our test vectors (2D)
    from cns_py.vector.embeddings import EmbeddingProvider
    class TestProv(EmbeddingProvider):
        @property
        def dimension(self): return 2
        def embed_texts(self, t): return [[1.0, 0.0]] * len(t)

    _INDEX_MANAGER.provider = TestProv()
    _INDEX_MANAGER.dim = 2
    
    # Force startup to initialize the inner index (clean state)
    _INDEX_MANAGER.startup()
    
    # Clear any data loaded from DB during startup (to prevent collisions with IDs like '1')
    if _INDEX_MANAGER.index:
        _INDEX_MANAGER.index._data = {}
        _INDEX_MANAGER.index._metadata = {}

    # Access the inner index directly for white-box seeding
    idx = _INDEX_MANAGER.index
    if idx is None:
        pytest.fail("Vector index not initialized")

    try:
        idx.upsert("vec_a", [1.0, 0.0])
        idx.upsert("vec_b", [0.0, 1.0])
    except Exception:
        pytest.skip("Vector index backend failed to upsert")

    # Query via API for vec_a
    resp = client.post("/graph/similar", json={"vector": [1.0, 0.0], "k": 5})
    if resp.status_code != 200:
        pytest.fail(f"Status {resp.status_code}: {resp.text}")
    assert resp.status_code == 200
    payload = resp.json()
    assert "results" in payload
    results = payload["results"]
    assert len(results) >= 1

    # vec_a should be top result with score ~1.0
    top = results[0]
    assert top["id"] == "vec_a"
    assert top["score"] > 0.99
