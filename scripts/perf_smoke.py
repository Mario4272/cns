from __future__ import annotations
import argparse
import json
import statistics
import time
from typing import List

from cns_py.cql.executor import cql


def run_once() -> float:
    q = 'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE'
    t0 = time.perf_counter()
    out = cql(q)
    t1 = time.perf_counter()
    # Persist last explain for artifacting
    try:
        with open("perf_last_explain.json", "w", encoding="utf-8") as f:
            json.dump(out.get("explain", {}), f, indent=2)
    except Exception:
        pass
    return (t1 - t0) * 1000.0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=15)
    ap.add_argument("--p95-budget-ms", type=float, default=500.0)
    args = ap.parse_args(argv)

    samples: List[float] = []
    # warmup
    for _ in range(3):
        _ = run_once()
    # measure
    for _ in range(args.iters):
        ms = run_once()
        samples.append(ms)
    samples.sort()
    idx = max(0, int(round(0.95 * len(samples))) - 1)
    p95 = samples[idx]
    summary = {
        "iters": args.iters,
        "samples_ms": samples,
        "p95_ms": p95,
        "budget_ms": args.p95_budget_ms,
        "pass": p95 <= args.p95_budget_ms,
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
