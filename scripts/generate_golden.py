
import json
import os
from datetime import datetime
from cns_py.cql.executor import cql

# Canonical query for receipts
QUERY = 'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2024-12-31T12:00:00Z RETURN EXPLAIN'
OUTPUT_PATH = "tests/golden/receipt_explain_v1.json"

def normalize(obj):
    """Recursively strip volatile fields."""
    if isinstance(obj, dict):
        # Strip timing fields
        if "total_ms" in obj:
            obj["total_ms"] = 0.0
        if "ms" in obj:
            obj["ms"] = 0.0
        # Recurse
        for k, v in obj.items():
            obj[k] = normalize(v)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = normalize(item)
    return obj

def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def main():
    print(f"Running query: {QUERY}")
    res = cql(QUERY)
    
    # Normalize
    cleaned = normalize(res)
    
    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, default=default_serializer, indent=2, sort_keys=True)
    
    print(f"Generated golden master at: {os.path.abspath(OUTPUT_PATH)}")

if __name__ == "__main__":
    main()
