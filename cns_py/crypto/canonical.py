"""
Canonicalization logic for Signed Provenance.
Enforces strict deterministic byte representation of JSON data.
follows proper subset of RFC 8785 (JCS).
"""
import json
from typing import Any


def canonicalize(data: Any) -> bytes:
    """
    Convert data to a canonical byte string.
    
    Rules:
    1. Keys sorted lexicographically.
    2. No whitespace (separators=(',', ':')).
    3. UTF-8 encoding.
    4. Floats are currently NOT verified for IEEE 754 bit-exactness in this version,
       refer to documentation. Ideally use strings or integers for claim values.
    
    Args:
        data: The JSON-serializable data (dict, list, str, int, etc.)
    
    Returns:
        bytes: The canonical UTF-8 encoded, sorted, compact JSON.
    """
    # sort_keys=True ensures deterministic ordering of dict keys
    # separators=(',', ':') ensures minimal whitespace (compact)
    # ensure_ascii=False allows UTF-8 characters to pass through unescaped (standard for JCS)
    json_str = json.dumps(
        data, 
        sort_keys=True, 
        separators=(',', ':'), 
        ensure_ascii=False
    )
    return json_str.encode('utf-8')
