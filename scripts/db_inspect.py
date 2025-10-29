from cns_py.storage.db import get_conn

with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM atoms")
        print("atoms", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM fibers")
        print("fibers", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM aspects")
        print("aspects", cur.fetchone()[0])
        cur.execute(
            "SELECT a_src.label, f.predicate, a_dst.label FROM fibers f "
            "JOIN atoms a_src ON a_src.id=f.src "
            "JOIN atoms a_dst ON a_dst.id=f.dst"
        )
        rows = cur.fetchall()
        print("edges", rows)
