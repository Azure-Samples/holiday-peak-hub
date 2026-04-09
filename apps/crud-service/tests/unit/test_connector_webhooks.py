"""Unit tests for connector webhook routes."""

from __future__ import annotations

from unittest.mock import AsyncMock

from crud_service.main import app
from crud_service.routes import connector_webhooks
from fastapi.testclient import TestClient


def test_connector_webhook_accepts_valid_payload(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(connector_webhooks.settings, "connector_sync_enabled", True)
    consumer_mock = AsyncMock()
    consumer_mock.ingest_webhook_event.return_value = "evt-123"
    monkeypatch.setattr(connector_webhooks, "connector_sync_consumer", consumer_mock)

    response = client.post(
        "/webhooks/connectors/akeneo",
        json={
            "event_type": "ProductChanged",
            "entity_id": "sku-1",
            "product_id": "sku-1",
            "name": "Demo",
        },
    )

    assert response.status_code == 202
    assert response.json()["event_id"] == "evt-123"
    assert response.json()["schema_version"] == "1.0"

    forwarded_payload = consumer_mock.ingest_webhook_event.await_args.args[0]
    assert forwarded_payload["schema_version"] == "1.0"
    assert forwarded_payload["source_system"] == "akeneo"


def test_connector_webhook_rejects_invalid_payload(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(connector_webhooks.settings, "connector_sync_enabled", True)
    consumer_mock = AsyncMock()
    monkeypatch.setattr(connector_webhooks, "connector_sync_consumer", consumer_mock)

    response = client.post(
        "/webhooks/connectors/akeneo",
        json={
            "event_type": "ProductChanged",
            "product_id": "sku-1",
        },
    )

    assert response.status_code == 400


def test_replay_dead_letters_route(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(connector_webhooks.settings, "connector_sync_enabled", True)
    consumer_mock = AsyncMock()
    consumer_mock.replay_unreplayed.return_value = {"replayed": 2, "failed": 0}
    monkeypatch.setattr(connector_webhooks, "connector_sync_consumer", consumer_mock)

    response = client.post("/webhooks/connectors/replay", json={"limit": 10})

    assert response.status_code == 200
    assert response.json()["replayed"] == 2
