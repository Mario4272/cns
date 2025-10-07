from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from dateutil.tz import UTC
from psycopg.types.json import Json

from cns_py.storage.db import get_conn


def upsert_atom(cur: Any, kind: str, label: str, text: str | None = None) -> int:
    cur.execute(
        """
        INSERT INTO atoms(kind, label, text)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (kind, label, text),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    # fetch existing id
    cur.execute("SELECT id FROM atoms WHERE kind=%s AND label=%s", (kind, label))
    return cur.fetchone()[0]


def link_with_validity(
    cur: Any,
    src_id: int,
    dst_id: int,
    predicate: str,
    valid_from: datetime | None,
    valid_to: datetime | None,
    belief: float | None = 1.0,
    provenance: Dict[str, Any] | None = None,
) -> None:
    cur.execute(
        """
        INSERT INTO fibers(src, dst, predicate) VALUES (%s, %s, %s) RETURNING id
        """,
        (src_id, dst_id, predicate),
    )
    fiber_id = cur.fetchone()[0]
    if provenance is None:
        provenance = {
            "source_id": f"demo_seed:fiber:{fiber_id}",
            "uri": "https://example.org/demo/tls-policy",
            "hash": "demo-sha256-placeholder",
            "fetched_at": datetime.now(tz=UTC).isoformat(),
            "line_span": None,
        }
    cur.execute(
        """
        INSERT INTO aspects(subject_kind, subject_id, valid_from, valid_to, belief, provenance)
        VALUES ('fiber', %s, %s, %s, %s, %s)
        ON CONFLICT (subject_kind, subject_id)
        DO UPDATE SET valid_from=excluded.valid_from,
                      valid_to=excluded.valid_to,
                      belief=excluded.belief,
                      provenance=excluded.provenance
        """,
        (fiber_id, valid_from, valid_to, belief, Json(provenance)),
    )
    return fiber_id


def main() -> None:
    # Define demo timeline
    cutoff = datetime(2025, 1, 1, tzinfo=UTC)

    with get_conn() as conn:
        with conn.cursor() as cur:
            framework = upsert_atom(cur, "Entity", "FrameworkX")
            tls12 = upsert_atom(cur, "Concept", "TLS1.2")
            tls13 = upsert_atom(cur, "Concept", "TLS1.3")

            # FrameworkX supports TLS1.2 until 2024-12-31 23:59:59
            link_with_validity(
                cur,
                framework,
                tls12,
                "supports_tls",
                valid_from=None,
                valid_to=cutoff,
                belief=0.95,
            )

            # From 2025-01-01, it supports TLS1.3
            link_with_validity(
                cur,
                framework,
                tls13,
                "supports_tls",
                valid_from=cutoff,
                valid_to=None,
                belief=0.98,
            )

    print("Demo data ingested: FrameworkX → TLS1.2 before 2025, TLS1.3 after 2025.")


if __name__ == "__main__":
    main()
