from typing import List

from cns_py.storage.db import get_conn


def nn_search(query: str, k: int = 5, space: str = "default") -> List[int]:
    q = f"%{query}%"
    ids: List[int] = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM atoms WHERE label ILIKE %(q)s "
                "ORDER BY LENGTH(label) ASC LIMIT %(k)s",
                {"q": q, "k": k},
            )
            rows = cur.fetchall()
            for (atom_id,) in rows:
                try:
                    ids.append(int(atom_id))
                except Exception:
                    continue
    return ids
