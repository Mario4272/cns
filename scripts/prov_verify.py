"""
Provenance verifier (dev placeholder).
Validates simple JSON provenance fields and prints a summary for a given fiber id.

Usage:
  python scripts/prov_verify.py --fiber-id 123
"""
from __future__ import annotations
import argparse
import json
from typing import Any

from cns_py.storage.db import get_conn


def verify_fiber_provenance(fiber_id: int) -> dict[str, Any]:
    sql = """
        SELECT asp.provenance
        FROM aspects asp
        WHERE asp.subject_kind='fiber' AND asp.subject_id=%s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (fiber_id,))
            row = cur.fetchone()
            if not row:
                return {"fiber_id": fiber_id, "ok": False, "error": "no aspects row"}
            prov = row[0]
            if prov is None:
                return {"fiber_id": fiber_id, "ok": False, "error": "provenance is NULL"}
            # Basic shape check
            ok = isinstance(prov, dict) and "source_id" in prov
            return {"fiber_id": fiber_id, "ok": ok, "provenance": prov}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fiber-id", type=int, required=True)
    args = ap.parse_args(argv)
    out = verify_fiber_provenance(args.fiber_id)
    print(json.dumps(out, indent=2, default=str))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
