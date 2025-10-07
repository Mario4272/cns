from __future__ import annotations

from datetime import datetime
from typing import Optional

from dateutil.tz import UTC

from cns_py.storage.db import get_conn


def tls_supported_as_of(label: str, ts: datetime) -> Optional[str]:
    sql = """
    SELECT a_dst.label AS tls_label
    FROM fibers f
    JOIN atoms a_src ON a_src.id = f.src
    JOIN atoms a_dst ON a_dst.id = f.dst
    JOIN aspects asp ON asp.subject_kind='fiber' AND asp.subject_id=f.id
    WHERE a_src.label=%s AND f.predicate='supports_tls'
      AND COALESCE(asp.valid_from, '-infinity'::timestamptz) <= %s
      AND COALESCE(asp.valid_to,   'infinity'::timestamptz)  >  %s
    ORDER BY COALESCE(asp.belief, 0) DESC
    LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (label, ts, ts))
            row = cur.fetchone()
            if row:
                return str(row[0])
    return None


def main() -> None:
    t_before = datetime(2024, 12, 31, 12, 0, tzinfo=UTC)
    t_after = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)

    v1 = tls_supported_as_of("FrameworkX", t_before)
    v2 = tls_supported_as_of("FrameworkX", t_after)

    print(f"As of {t_before.isoformat()} -> {v1}")
    print(f"As of {t_after.isoformat()} -> {v2}")


if __name__ == "__main__":
    main()
