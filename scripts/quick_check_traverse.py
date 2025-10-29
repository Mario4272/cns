from cns_py.graph import traverse_from
from cns_py.storage.db import DbConfig, get_conn

cfg = DbConfig()
print("DB using", cfg.dbname)
with get_conn(cfg) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM atoms WHERE label=%s", ("FrameworkX",))
        row = cur.fetchone()
        print("framework row", row)
        if not row:
            raise SystemExit(1)
        fid = int(row[0])
        cur.execute(
            "SELECT a_src.label, f.predicate, a_dst.label FROM fibers f "
            "JOIN atoms a_src ON a_src.id=f.src "
            "JOIN atoms a_dst ON a_dst.id=f.dst "
            "WHERE f.src=%s",
            (fid,),
        )
        edges = cur.fetchall()
        print("fibers edges", edges)

edges2 = traverse_from([fid], hops=1, predicates=["supports_tls"], limit=100)
print("traverse_from edges", edges2)
