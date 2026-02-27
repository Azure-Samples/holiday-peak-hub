from crm_support_assistance.main import app
from fastapi.testclient import TestClient


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "crm-support-assistance"


def test_invoke_requires_contact_id():
    client = TestClient(app)
    resp = client.post("/invoke", json={})
    assert resp.status_code == 200
    assert resp.json().get("error") == "contact_id is required"
