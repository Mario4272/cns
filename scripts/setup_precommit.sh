#!/bin/bash
# Setup pre-commit hooks for CNS
# Run this once to install pre-commit hooks

set -e

echo "Setting up pre-commit hooks for CNS..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found in PATH"
    exit 1
fi

# Install pre-commit if not already installed
echo "Installing pre-commit..."
python3 -m pip install pre-commit

# Install the git hooks
echo "Installing git hooks..."
pre-commit install

# Run hooks on all files to verify setup
echo "Running hooks on all files (this may take a minute)..."
pre-commit run --all-files || true

echo ""
echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "From now on, hooks will run automatically on 'git commit'"
echo "To run manually: pre-commit run --all-files"
