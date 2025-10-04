# Requires: GitHub CLI (gh) authenticated
# Usage: .\scripts\create_issues.ps1 -Repo "owner/repo"
param(
  [Parameter(Mandatory=$true)][string]$Repo
)

$tasks = @(
  @{ Title = 'P1: CQL v0.1 parser';       Body = 'Grammar + unit tests';                               Labels = 'phase/P1,cql,area/python' },
  @{ Title = 'P1: Executor pipeline';      Body = 'ANN→ASOF mask→traverse';                             Labels = 'phase/P1,area/python,perf' },
  @{ Title = 'P1: Citations in results';   Body = 'source_id, uri, hash, line_span';                    Labels = 'phase/P1,docs,api' },
  @{ Title = 'P1: EXPLAIN timings';        Body = 'operator timings + fanout';                          Labels = 'phase/P1,perf' },
  @{ Title = 'P1: Belief v0';              Body = 'logistic + config + docs';                           Labels = 'phase/P1,area/python' },
  @{ Title = 'P1: Golden tests';           Body = 'ASOF split, citations, belief thresholds';           Labels = 'phase/P1,tests' },
  @{ Title = 'P1: Latency target';         Body = 'P95 ≤ 300 ms on dev corpus';                         Labels = 'phase/P1,perf' },
  @{ Title = 'P1: README CQL example';     Body = 'time-split + citations + EXPLAIN';                   Labels = 'phase/P1,docs' }
)

foreach ($t in $tasks) {
  $url = gh issue create -R $Repo -t $t.Title -b $t.Body -l $t.Labels
  if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create issue: $($t.Title)"
    exit 1
  }
  if ($url -match '/issues/([0-9]+)$') {
    $num = $matches[1]
    Write-Output "$($t.Title) -> #$num"
  } else {
    Write-Output "$($t.Title) -> $url"
  }
}
