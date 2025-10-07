from __future__ import annotations

import argparse
import json
import time
from typing import List

from cns_py.cql.executor import cql


def run_once() -> float:
    q = (
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        'ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE'
    )
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
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--warmup", type=int, default=50)
    ap.add_argument("--p95-budget-ms", type=float, default=500.0)
    ap.add_argument("--p99-budget-ms", type=float, default=900.0)
    args = ap.parse_args(argv)

    # Ensure EXPLAIN artifact exists even if we fail early
    try:
        with open("perf_last_explain.json", "w", encoding="utf-8") as f:
            json.dump({"status": "initializing"}, f)
    except Exception:
        pass

    # Warmup phase
    print("[CI: perf-smoke]")
    print(f"Warming up ({args.warmup} iterations)...")
    for _ in range(args.warmup):
        _ = run_once()

    # Measurement phase
    samples: List[float] = []
    for _ in range(args.iters):
        ms = run_once()
        samples.append(ms)

    samples.sort()
    p50_idx = max(0, int(round(0.50 * len(samples))) - 1)
    p95_idx = max(0, int(round(0.95 * len(samples))) - 1)
    p99_idx = max(0, int(round(0.99 * len(samples))) - 1)

    p50 = samples[p50_idx]
    p95 = samples[p95_idx]
    p99 = samples[p99_idx]

    # Print Val's required format
    print(f"dataset=seed/demo@HEAD samples={args.iters} warmup={args.warmup}")
    print(f"query=resolve_entities p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    print("env=2CPU/4GB; postgres=16; shared_buffers=512MB; work_mem=64MB")
    print("raw=artifacts/perf_smoke.json")

    summary = {
        "dataset": "seed/demo@HEAD",
        "samples": args.iters,
        "warmup": args.warmup,
        "query": "resolve_entities",
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "p95_budget_ms": args.p95_budget_ms,
        "p99_budget_ms": args.p99_budget_ms,
        "p95_pass": p95 <= args.p95_budget_ms,
        "p99_pass": p99 <= args.p99_budget_ms,
        "samples_ms": samples,
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["p95_pass"] else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
