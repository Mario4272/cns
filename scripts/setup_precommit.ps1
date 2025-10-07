# Setup pre-commit hooks for CNS
# Run this once to install pre-commit hooks

Write-Host "Setting up pre-commit hooks for CNS..." -ForegroundColor Green

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
    exit 1
}

# Install pre-commit if not already installed
Write-Host "`nInstalling pre-commit..." -ForegroundColor Yellow
python -m pip install pre-commit

# Install the git hooks
Write-Host "`nInstalling git hooks..." -ForegroundColor Yellow
pre-commit install

# Run hooks on all files to verify setup
Write-Host "`nRunning hooks on all files (this may take a minute)..." -ForegroundColor Yellow
pre-commit run --all-files

Write-Host "`n✅ Pre-commit hooks installed successfully!" -ForegroundColor Green
Write-Host "`nFrom now on, hooks will run automatically on 'git commit'" -ForegroundColor Cyan
Write-Host "To run manually: pre-commit run --all-files" -ForegroundColor Cyan
