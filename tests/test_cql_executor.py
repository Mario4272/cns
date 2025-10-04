import json
import os
from cns_py.cql.executor import cql


def load_golden(name: str) -> dict:
    here = os.path.dirname(__file__)
    path = os.path.join(here, "golden", name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_cql_golden_asof_2025():
    g = load_golden("cql_asof_2025.json")
    out = cql(g["query"])
    assert "results" in out and len(out["results"]) >= 1

    top = out["results"][0]
    # check expected top fields
    for k, v in g["expect_top"].items():
        assert top.get(k) == v
    # required keys present
    for k in g["expect_keys"]:
        assert k in top
    # at least one citation
    assert isinstance(top.get("provenance"), list) and len(top["provenance"]) >= 1

    # explain steps contain required sequence (order-insensitive presence)
    steps = [s.get("name") for s in out.get("explain", {}).get("steps", [])]
    for name in g["expect_explain_steps"]:
        assert name in steps
