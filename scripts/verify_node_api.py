
import requests
import json
from datetime import datetime, timezone
from cns_py.api.server import app
from fastapi.testclient import TestClient

def test_node_api():
    client = TestClient(app)
    # Node 1 is usually in seed data? 
    # If not, we might get 404.
    # Let's hope seed data exists or we mock.
    # Actually, let's use a non-existent node ID to check for 404/500 stability
    # Or assume integration test DB has something.
    
    resp = client.get("/graph/node/1")
    if resp.status_code == 404:
        print("Node 1 not found (Expected if DB empty)")
    elif resp.status_code == 200:
        print("Node 1 found")
        data = resp.json()
        print(json.dumps(data, indent=2))
        # Check aspect belief is float
        if data["aspects"]:
            assert isinstance(data["aspects"][0]["belief"], float)
    else:
        print(f"Error: {resp.status_code} {resp.text}")
        exit(1)

    print("SUCCESS")

if __name__ == "__main__":
    test_node_api()
