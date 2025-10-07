import json
import sys
import traceback
from pathlib import Path

# Ensure project root (one level up from scripts/) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from cns_py.cql.executor import cql

    q = (
        'MATCH label="FrameworkX" PREDICATE supports_tls '
        "ASOF 2025-01-01T00:00:00Z RETURN EXPLAIN PROVENANCE"
    )
    print(json.dumps(cql(q), indent=2))
except Exception:
    traceback.print_exc()
