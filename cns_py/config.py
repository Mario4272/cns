import os


def temporal_predicate() -> str:
    """Return SQL fragment for end boundary based on config.
    Uses parameter %(ts_to)s for the upper bound.
    Default: exclusive end (valid_to > ts_to) with NULL treated as infinity.
    When CNS_ASOF_END_INCLUSIVE=1, use inclusive end (valid_to >= ts_to).
    """
    inclusive = os.getenv("CNS_ASOF_END_INCLUSIVE", "0") == "1"
    op = ">=" if inclusive else ">"
    return f"COALESCE(asp.valid_to,   'infinity'::timestamptz)  {op}  %(ts_to)s"


def vector_index_enabled() -> bool:
    """Return True if vector indexing is enabled."""
    return os.getenv("VECTOR_INDEX_ENABLED", "0") == "1"


def vector_index_backend() -> str:
    """Return the vector index backend type ('memory' or 'pg')."""
    return os.getenv("VECTOR_INDEX_BACKEND", "memory").lower()


def vector_index_path() -> str:
    """Return the filesystem path/prefix for index persistence (memory backend)."""
    # Default to a safe relative path in case it's not set
    return os.getenv("VECTOR_INDEX_PATH", ".cns_vector_index/index")
