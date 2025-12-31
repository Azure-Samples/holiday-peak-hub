from fastapi.testclient import TestClient
from crm_profile_aggregation.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "crm-profile-aggregation"
