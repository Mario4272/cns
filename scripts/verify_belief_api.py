import json
from datetime import datetime, timezone


def test_api():
    # We can't easily spin up the server in a script without uvicorn/background process issues
    # in this env. Instead, we import the app and use TestClient.
    from fastapi.testclient import TestClient

    from cns_py.api.server import app

    client = TestClient(app)

    # Test Payload
    payload = {
        "base_belief": 1.0,
        "observed_at_pipeline_iso": datetime.now(timezone.utc).isoformat(),
        "provenance_count": 0,
        "contradiction_count": 1,
    }

    resp = client.post("/belief/explain", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Body: {json.dumps(resp.json(), indent=2)}")

    assert resp.status_code == 200
    data = resp.json()
    assert abs(data["final_score"] - 0.5) < 0.0001
    print("SUCCESS")


if __name__ == "__main__":
    test_api()
