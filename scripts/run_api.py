#!/usr/bin/env python3
"""Run the CNS FastAPI server locally.

Usage:
    python -m scripts.run_api [--host 127.0.0.1] [--port 8000] [--reload]
"""

import argparse
import sys
from pathlib import Path

import uvicorn

from cns_py.api.server import get_app

# Add repo root to sys.path so we can import cns_py.api.server
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CNS FastAPI server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    app = get_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
