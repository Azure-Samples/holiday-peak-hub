from fastapi.testclient import TestClient
from logistics_eta_computation.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "logistics-eta-computation"
