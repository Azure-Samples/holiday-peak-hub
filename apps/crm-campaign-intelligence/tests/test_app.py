from fastapi.testclient import TestClient
from crm_campaign_intelligence.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "crm-campaign-intelligence"


def test_invoke_returns_service():
    client = TestClient(app)
    resp = client.post("/invoke", json={"query": ""})
    assert resp.status_code == 200
    assert resp.json()["service"] == "crm-campaign-intelligence"
