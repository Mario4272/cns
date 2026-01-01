from __future__ import annotations

import argparse
import json
import time
from typing import Dict, List, Tuple

from cns_py.cql.executor import cql

Query = Tuple[str, str]


def _extract_timings(explain: Dict) -> Dict[str, float]:
    # explain contains steps=[{name, ms, extra}], total_ms
    out = {"ann_ms": 0.0, "mask_ms": 0.0, "traverse_ms": 0.0, "rules_ms": 0.0}
    for s in explain.get("steps", []):
        name = s.get("name")
        ms = float(s.get("ms") or 0.0)
        if name == "ann_shortlist":
            out["ann_ms"] = ms
        elif name == "temporal_mask":
            out["mask_ms"] = ms
        elif name == "graph_traverse":
            out["traverse_ms"] = ms
        elif name == "belief_compute":
            out["rules_ms"] = ms
    return out


def run_once(query: str) -> Tuple[float, Dict]:
    t0 = time.perf_counter()
    out = cql(query)
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0, out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--warmup", type=int, default=50)
    # Conservative local target: flag if p95 exceeds ~500ms.
    ap.add_argument("--p95-budget-ms", type=float, default=500.0)
    ap.add_argument("--p99-budget-ms", type=float, default=900.0)
    args = ap.parse_args(argv)

    QUERIES: List[Query] = [
        (
            "asof_2024",
            'MATCH label="FrameworkX" PREDICATE supports_tls '
            "ASOF 2024-12-31T12:00:00Z RETURN EXPLAIN PROVENANCE",
        ),
        (
            "asof_2025",
            'MATCH label="FrameworkX" PREDICATE supports_tls '
            "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE",
        ),
    ]

    # Ensure artifacts exist even if we fail early
    try:
        with open("perf_last_explain.json", "w", encoding="utf-8") as f:
            json.dump({"status": "initializing"}, f)
        with open("perf_summary.md", "w", encoding="utf-8") as f:
            f.write("# Perf Smoke Summary\ninitializing\n")
    except Exception:
        pass

    # Warmup
    print("[CI: perf-smoke]")
    print(f"Warming up ({args.warmup} iterations per query)...")
    for name, q in QUERIES:
        for _ in range(args.warmup):
            _ms, _ = run_once(q)

    # Measurement
    result_rows: List[Dict] = []
    for name, q in QUERIES:
        samples: List[float] = []
        last_explain: Dict = {}
        last_rows = 0
        # For determinism we care about the stable identity of winners, not
        # volatile fields like timestamps or provenance payloads. Use a
        # canonical sorted list of fiber_ids as the comparison key.
        canonical_fiber_ids: List[int] | None = None
        deterministic = True
        for _ in range(args.iters):
            ms, out = run_once(q)
            samples.append(ms)
            if isinstance(out, dict):
                last_explain = out.get("explain", {}) or {}
                results = out.get("results", []) or []
                last_rows = len(results)

                # Determinism check: build a stable signature from fiber_ids when present.
                fiber_ids = sorted(
                    int(r["fiber_id"]) for r in results if r.get("fiber_id") is not None
                )
                if canonical_fiber_ids is None:
                    canonical_fiber_ids = fiber_ids
                elif deterministic and fiber_ids != canonical_fiber_ids:
                    deterministic = False

        samples.sort()
        p50_idx = max(0, int(round(0.50 * len(samples))) - 1)
        p95_idx = max(0, int(round(0.95 * len(samples))) - 1)
        p99_idx = max(0, int(round(0.99 * len(samples))) - 1)
        p50 = samples[p50_idx]
        p95 = samples[p95_idx]
        p99 = samples[p99_idx]
        timings = _extract_timings(last_explain)

        # Persist explain for the last query
        try:
            with open("perf_last_explain.json", "w", encoding="utf-8") as f:
                json.dump(last_explain, f, indent=2)
        except Exception:
            pass

        row = {
            "name": name,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "rows": last_rows,
            "deterministic": deterministic,
            **timings,
        }
        result_rows.append(row)

    # Summarize
    summary_lines = ["# Perf Smoke Summary"]
    any_nondet = any(not r["deterministic"] for r in result_rows)

    for r in result_rows:
        summary_lines.append(
            (
                f"- **{r['name']}**: p50={r['p50_ms']:.1f}ms "
                f"p95={r['p95_ms']:.1f}ms p99={r['p99_ms']:.1f}ms "
                f"· rows={r['rows']} · deterministic={r['deterministic']} "
                f"· ann/mask/trav/rules="
                f"{r['ann_ms']:.1f}/{r['mask_ms']:.1f}/"
                f"{r['traverse_ms']:.1f}/{r['rules_ms']:.1f}ms"
            )
        )
    try:
        with open("perf_summary.md", "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines) + "\n")
    except Exception:
        pass

    # Gate on determinism and worst p95 across queries
    worst_p95 = max(r["p95_ms"] for r in result_rows) if result_rows else 0.0
    if any_nondet:
        print("[perf-smoke] Non-deterministic results detected; failing.")
        return 1

    return 0 if worst_p95 <= args.p95_budget_ms else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
