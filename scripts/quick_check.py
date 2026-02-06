from cns_py.api.server import graph_neighborhood
from cns_py.storage.db import get_conn


def check():
    print("Checking for SuperHub...")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM atoms WHERE label='SuperHub'")
            row = cur.fetchone()
            if row:
                print(f"SuperHub found: {row[0]}")
                # Check edges
                cur.execute("SELECT count(*) FROM fibers WHERE src=%s", (row[0],))
                print(f"Edges: {cur.fetchone()[0]}")
            else:
                print("SuperHub not found. Checking FrameworkX...")
                cur.execute("SELECT id FROM atoms WHERE label='FrameworkX'")
                row = cur.fetchone()
                if row:
                    print(f"FrameworkX found: {row[0]}")
                    cur.execute("SELECT count(*) FROM fibers WHERE src=%s", (row[0],))
                    print(f"Edges: {cur.fetchone()[0]}")

    print("\nTest Pagination (Limit 1, Offset 0)...")
    res1 = graph_neighborhood("FrameworkX", limit=1, offset=0)
    print(f"Page 1: {len(res1.nodes)} nodes")
    if res1.nodes:
        print(f"  Node: {res1.nodes[0].label}")

    print("\nTest Pagination (Limit 1, Offset 1)...")
    res2 = graph_neighborhood("FrameworkX", limit=1, offset=1)
    print(f"Page 2: {len(res2.nodes)} nodes")
    if res2.nodes:
        print(f"  Node: {res2.nodes[0].label}")

    if res1.nodes and res2.nodes and res1.nodes[0].label != res2.nodes[0].label:
        print("\nSUCCESS: Offset returned different result.")
    elif not res1.nodes:
        print("\nSKIP: Not enough data to test offset.")
    else:
        print("\nFAIL: Offset returned same result?")


if __name__ == "__main__":
    check()
