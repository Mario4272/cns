import time

from cns_py.api.server import graph_neighborhood
from cns_py.demo.ingest import upsert_atom
from cns_py.storage.db import get_conn

HUB_LABEL = "SuperHub"
TARGET_COUNT = 1500


def setup_data():
    print(f"Ensuring {HUB_LABEL} with {TARGET_COUNT} edges...")
    with get_conn() as conn:
        with conn.cursor() as cur:
            hub_id = upsert_atom(cur, "Hub", HUB_LABEL)

            # Check existing count
            cur.execute("SELECT count(*) FROM fibers WHERE src=%s", (hub_id,))
            count = cur.fetchone()[0]
            if count >= TARGET_COUNT:
                print(f"Data exists ({count} edges). Skipping ingest.")
                return hub_id

            # Bulk ingest attempt
            print(f"Bulk ingesting {TARGET_COUNT - count} edges...")

            # 1. Generate args for atoms
            new_labels = [f"Leaf_{i:05d}" for i in range(count, TARGET_COUNT)]
            # (kind, label)
            atom_args = [("Leaf", lbl) for lbl in new_labels]

            # Bulk upsert atoms
            print("  Inserting atoms...")
            # Fallback: Just insert, we assume they don't exist for this bench.
            cur.executemany(
                "INSERT INTO atoms (kind, label) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                atom_args,
            )

            # Fetch all IDs
            print("  Fetching IDs...")
            cur.execute("SELECT id FROM atoms WHERE label = ANY(%s)", (new_labels,))
            target_ids = [r[0] for r in cur.fetchall()]

            print(f"  Got {len(target_ids)} target IDs. Linking...")

            # 2. Generate args for fibers (src, dst, predicate)
            fiber_args = [(hub_id, tid, "connects_to") for tid in target_ids]
            cur.executemany(
                "INSERT INTO fibers (src, dst, predicate) VALUES (%s, %s, %s)",
                fiber_args,
            )

            conn.commit()
            print("Done bulk ingest.")
            return hub_id


def benchmark():
    print("Warming up...")
    try:
        graph_neighborhood(HUB_LABEL, limit=100)
    except Exception as e:
        print(f"Warmup failed: {e}")

    samples = []
    print("Running benchmark (Fetch Page 1: Limit 100, Offset 0)...")
    for _ in range(20):
        t0 = time.perf_counter()
        # Requesting limit=100 (simulating page 1)
        res = graph_neighborhood(HUB_LABEL, limit=100, offset=0)
        dt = (time.perf_counter() - t0) * 1000
        samples.append(dt)
        assert len(res.nodes) <= 100, f"Limit assumption failed: got {len(res.nodes)}"

    samples.sort()
    p50 = samples[int(len(samples) * 0.5)]
    p95 = samples[int(len(samples) * 0.95)]
    print(f"Result (Page 1): P50={p50:.2f}ms, P95={p95:.2f}ms")

    # Test Offset
    print("Running benchmark (Fetch Page 2: Limit 100, Offset 100)...")
    t0 = time.perf_counter()
    res2 = graph_neighborhood(HUB_LABEL, limit=100, offset=100)
    dt2 = (time.perf_counter() - t0) * 1000
    print(f"Result (Page 2): {dt2:.2f}ms. Items: {len(res2.nodes)}")

    # Ensure items diff
    # print(f"Page 1 node 0: {res.nodes[0] if res.nodes else 'None'}")
    # print(f"Page 2 node 0: {res2.nodes[0] if res2.nodes else 'None'}")


if __name__ == "__main__":
    setup_data()
    benchmark()
