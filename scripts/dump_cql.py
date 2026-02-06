import json
from datetime import datetime

from cns_py.cql.executor import cql


# Custom serializer for datetime
def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


q = 'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2024-12-31T12:00:00Z RETURN EXPLAIN'
res = cql(q)
print(json.dumps(res, default=default_serializer, indent=2))
