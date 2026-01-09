
# CNS Beta Demo Runbook
# Usage: .\scripts\cns_beta_demo.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting CNS Beta Demo Sequence..." -ForegroundColor Cyan

# 0. Environment Check
if (-not (Test-Path ".venv")) {
    Write-Error "Virtual environment not found! Please run setup first."
}

# 1. Reset Database
Write-Host "`n[1/3] Resetting Database & Index..." -ForegroundColor Yellow
$env:CNS_DB_HOST="127.0.0.1"
$env:CNS_DB_PORT="5433"
$env:CNS_DB_NAME="cns"
$env:CNS_DB_USER="cns"
$env:CNS_DB_PASSWORD="cns"
$env:CNS_VECTOR_DIMS="1536"

# Run DB Reset (using python -m for module access)
# We assume .venv is active in current shell or we call python directly
# We trust the user is running this from a shell where `python` is the venv python
# or we can explicitly try to use the venv python
$PYTHON = "python"
if (Test-Path ".venv/Scripts/python.exe") {
    $PYTHON = ".venv/Scripts/python.exe"
}

& $PYTHON -m cns_py.storage.db --init
if ($LASTEXITCODE -ne 0) { throw "DB Init Failed" }

# 2. Ingest Seed Data
Write-Host "`n[2/3] Ingesting Seed Data (Phase 12 Demo Set)..." -ForegroundColor Yellow
& $PYTHON -m cns_py.demo.ingest
if ($LASTEXITCODE -ne 0) { throw "Ingest Failed" }

# 3. Run Showcase
Write-Host "`n[3/3] Running Showcase..." -ForegroundColor Yellow
& $PYTHON scripts/showcase_v1.py

Write-Host "`n✅ Demo Complete." -ForegroundColor Green
