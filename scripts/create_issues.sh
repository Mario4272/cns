#!/usr/bin/env bash
set -euo pipefail
# Usage: scripts/create_issues.sh owner/repo
REPO="${1:-}"
[[ -z "$REPO" ]] && { echo "Usage: $0 owner/repo"; exit 1; }

# Map of "Title|Body|Labels"
tasks=(
  "P1: CQL v0.1 parser|Grammar + unit tests|phase/P1,cql,area/python"
  "P1: Executor pipeline|ANN→ASOF mask→traverse|phase/P1,area/python,perf"
  "P1: Citations in results|source_id, uri, hash, line_span|phase/P1,docs,api"
  "P1: EXPLAIN timings|operator timings + fanout|phase/P1,perf"
  "P1: Belief v0|logistic + config + docs|phase/P1,area/python"
  "P1: Golden tests|ASOF split, citations, belief thresholds|phase/P1,tests"
  "P1: Latency target|P95 ≤ 300 ms on dev corpus|phase/P1,perf"
  "P1: README CQL example|time-split + citations + EXPLAIN|phase/P1,docs"
)

for t in "${tasks[@]}"; do
  IFS="|" read -r title body labels <<<"$t"
  url=$(gh issue create -R "$REPO" -t "$title" -b "$body" -l "$labels")
  num=$(sed -E 's#.*/issues/([0-9]+)#\1#' <<<"$url")
  echo "$title -> #$num"
done
