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
