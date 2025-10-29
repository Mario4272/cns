import os

from cns_py.storage.db import get_conn
from tests.admin_db import drop_db, make_ephemeral_db

if __name__ == "__main__":
    dsn = make_ephemeral_db()
    dbname = next((p.split("=")[1] for p in dsn.split() if p.startswith("dbname=")), None)
    os.environ["CNS_DB_NAME"] = dbname or ""
    print("DB", dbname)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM atoms")
            print("atoms", cur.fetchone()[0])
            cur.execute(
                "SELECT a_src.label, f.predicate, a_dst.label FROM fibers f "
                "JOIN atoms a_src ON a_src.id=f.src "
                "JOIN atoms a_dst ON a_dst.id=f.dst "
                "WHERE f.predicate='supports_tls'"
            )
            edges = cur.fetchall()
            print("edges", edges)
    drop_db(dbname)
