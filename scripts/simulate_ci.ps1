$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Local CI Simulation..." -ForegroundColor Cyan

# 1. Ruff Linting
Write-Host "`n🔍 Running Ruff Linting..." -ForegroundColor Yellow
ruff check .
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Ruff Linting Passed" -ForegroundColor Green } else { Write-Host "❌ Ruff Linting Failed" -ForegroundColor Red; exit 1 }

# 2. Ruff Formatting Check
Write-Host "`n🎨 Running Ruff Format Check..." -ForegroundColor Yellow
ruff format --check .
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Ruff Format Check Passed" -ForegroundColor Green } else { Write-Host "❌ Ruff Format Check Failed" -ForegroundColor Red; exit 1 }

# 3. Black Formatting Check
Write-Host "`n⚫ Running Black Format Check..." -ForegroundColor Yellow
black --check .
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Black Format Check Passed" -ForegroundColor Green } else { Write-Host "❌ Black Format Check Failed" -ForegroundColor Red; exit 1 }

# 4. Mypy Type Checking
Write-Host "`n🧠 Running Mypy Type Checking..." -ForegroundColor Yellow
mypy .
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Mypy Passed" -ForegroundColor Green } else { Write-Host "❌ Mypy Failed" -ForegroundColor Red; exit 1 }

# 5. Pytest
Write-Host "`n🧪 Running Pytest..." -ForegroundColor Yellow
pytest
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Pytest Passed" -ForegroundColor Green } else { Write-Host "❌ Pytest Failed" -ForegroundColor Red; exit 1 }

Write-Host "`n🎉 All Checks Passed! You are ready to push." -ForegroundColor Cyan
