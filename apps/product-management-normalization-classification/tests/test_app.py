from fastapi.testclient import TestClient
from product_management_normalization_classification.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "product-management-normalization-classification"
