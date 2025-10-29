from typing import List, Optional, Sequence, Tuple

from cns_py.storage.db import get_conn

Edge = Tuple[str, str, str]


def traverse_from(
    ids: Sequence[int],
    hops: int = 1,
    predicates: Optional[Sequence[str]] = None,
    limit: int = 1000,
) -> List[Edge]:
    if not ids:
        return []

    # Use lists for psycopg array adaptation and cast to specific array types in SQL
    ids_list: List[int] = [int(i) for i in ids]
    preds_clause = ""
    params: dict[str, object] = {"limit": int(limit)}
    # Build explicit placeholders for ids to avoid ANY(array) adapter issues
    id_placeholders = ", ".join([f"%(id_{idx})s" for idx, _ in enumerate(ids_list)])
    for idx, val in enumerate(ids_list):
        params[f"id_{idx}"] = val
    if predicates:
        preds_list: List[str] = [str(p) for p in predicates]
        if len(preds_list) == 1:
            preds_clause = " AND f.predicate = %(pred)s"
            params["pred"] = preds_list[0]
        else:
            preds_clause = " AND f.predicate = ANY(%(preds)s::text[])"
            params["preds"] = preds_list

    results: List[Edge] = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            if hops <= 1:
                sql = (
                    "SELECT a_src.label, f.predicate, a_dst.label "
                    "FROM fibers f "
                    "JOIN atoms a_src ON a_src.id = f.src "
                    "JOIN atoms a_dst ON a_dst.id = f.dst "
                    f"WHERE f.src IN ({id_placeholders})" + preds_clause + " LIMIT %(limit)s"
                )
                cur.execute(sql, params)
                for row in cur.fetchall():
                    results.append((str(row[0]), str(row[1]), str(row[2])))
                return results

            # 2-hop traversal
            sql2 = (
                "SELECT a1.label, f1.predicate, a2.label "
                "FROM fibers f1 "
                "JOIN fibers f2 ON f1.dst = f2.src "
                "JOIN atoms a1 ON a1.id = f1.src "
                "JOIN atoms a2 ON a2.id = f2.dst "
                f"WHERE f1.src IN ({id_placeholders})" + preds_clause + " LIMIT %(limit)s"
            )
            cur.execute(sql2, params)
            for row in cur.fetchall():
                results.append((str(row[0]), str(row[1]), str(row[2])))
    return results
