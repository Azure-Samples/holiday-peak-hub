"""Unit tests for Truth Ingestion routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from truth_ingestion.main import app
from truth_ingestion.routes import set_adapters


@pytest.fixture(autouse=True)
def inject_mock_adapters(mock_adapters):
    """Inject mock adapters into routes before each test."""
    set_adapters(mock_adapters)
    yield
    set_adapters(None)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "truth-ingestion"


class TestIngestProductEndpoint:
    def test_ingest_product_success(self, sample_pim_product):
        client = TestClient(app)
        response = client.post(
            "/ingest/product",
            json={"product": sample_pim_product},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["result"]["entity_id"] == "PROD-001"

    def test_ingest_product_missing_payload(self):
        client = TestClient(app)
        response = client.post("/ingest/product", json={})
        assert response.status_code == 422  # Pydantic validation error


class TestBulkIngestEndpoint:
    def test_bulk_ingest_success(self, sample_pim_product, sample_pim_product_no_variants):
        client = TestClient(app)
        response = client.post(
            "/ingest/bulk",
            json={"products": [sample_pim_product, sample_pim_product_no_variants]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["total"] == 2
        assert data["succeeded"] == 2
        assert data["failed"] == 0

    def test_bulk_ingest_empty_list_rejected(self):
        client = TestClient(app)
        response = client.post("/ingest/bulk", json={"products": []})
        assert response.status_code == 422


class TestSyncEndpoint:
    def test_trigger_sync_returns_job_id(self):
        client = TestClient(app)
        response = client.post("/ingest/sync", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "job_id" in data


class TestJobStatusEndpoint:
    def test_get_existing_job_status(self):
        client = TestClient(app)
        # First create a job via sync
        sync_response = client.post("/ingest/sync", json={})
        job_id = sync_response.json()["job_id"]

        status_response = client.get(f"/ingest/status/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["type"] == "sync"

    def test_get_nonexistent_job_returns_404(self):
        client = TestClient(app)
        response = client.get("/ingest/status/nonexistent-job-id")
        assert response.status_code == 404


class TestWebhookEndpoint:
    def test_webhook_product_created(self, sample_pim_product):
        client = TestClient(app)
        response = client.post(
            "/ingest/webhook",
            json={
                "event_type": "product.created",
                "entity_id": "PROD-001",
                "data": sample_pim_product,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

    def test_webhook_product_updated(self, sample_pim_product):
        client = TestClient(app)
        response = client.post(
            "/ingest/webhook",
            json={
                "event_type": "product.updated",
                "entity_id": "PROD-001",
                "data": sample_pim_product,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    def test_webhook_unknown_event_skipped(self):
        client = TestClient(app)
        response = client.post(
            "/ingest/webhook",
            json={"event_type": "order.created"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"

    def test_webhook_missing_data_skipped(self):
        client = TestClient(app)
        response = client.post(
            "/ingest/webhook",
            json={"event_type": "product.created"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"
