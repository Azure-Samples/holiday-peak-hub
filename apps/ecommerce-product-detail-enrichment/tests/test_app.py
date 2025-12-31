from fastapi.testclient import TestClient
from ecommerce_product_detail_enrichment.main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-product-detail-enrichment"
