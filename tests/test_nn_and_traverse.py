from __future__ import annotations

from typing import List

from cns_py.graph import traverse_from
from cns_py.nn import nn_search
from cns_py.storage.db import get_conn


def _get_label(atom_id: int) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT label FROM atoms WHERE id=%s", (atom_id,))
            row = cur.fetchone()
            assert row is not None, f"Atom id {atom_id} not found"
            return str(row[0])


def _get_id_by_label(label: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM atoms WHERE label=%s", (label,))
            row = cur.fetchone()
            assert row is not None, f"Atom with label {label} not found"
            return int(row[0])


def test_nn_search_returns_frameworkx_id():
    ids: List[int] = nn_search("FrameworkX", k=3)
    assert len(ids) >= 1
    labels = {_get_label(i) for i in ids}
    assert "FrameworkX" in labels


def test_traverse_from_one_hop_supports_tls():
    framework_id = _get_id_by_label("FrameworkX")
    edges = traverse_from([framework_id], hops=1, predicates=["supports_tls"], limit=100)
    # Expect edges to TLS1.2 and TLS1.3 as per demo ingest
    assert ("FrameworkX", "supports_tls", "TLS1.2") in edges or (
        "FrameworkX",
        "supports_tls",
        "TLS1_2",
    ) in edges
    assert ("FrameworkX", "supports_tls", "TLS1.3") in edges or (
        "FrameworkX",
        "supports_tls",
        "TLS1_3",
    ) in edges
