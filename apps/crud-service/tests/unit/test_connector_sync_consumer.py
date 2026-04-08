"""Unit tests for connector synchronization consumer."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from crud_service.consumers.connector_sync import ConnectorSyncConsumer


@pytest.mark.asyncio
async def test_duplicate_event_is_ignored(monkeypatch) -> None:
    consumer = ConnectorSyncConsumer()

    processed_repo = AsyncMock()
    processed_repo.is_processed.return_value = True
    monkeypatch.setattr(consumer, "_processed_repo", processed_repo)
    monkeypatch.setattr(consumer, "_dead_letter_repo", AsyncMock())

    process_product_changed = AsyncMock()
    monkeypatch.setattr(consumer, "_process_product_changed", process_product_changed)

    payload = {
        "event_id": "evt-1",
        "event_type": "ProductChanged",
        "source_system": "akeneo",
        "entity_id": "sku-1",
        "product_id": "sku-1",
    }

    await consumer.process_payload(payload)

    process_product_changed.assert_not_called()
    processed_repo.mark_processed.assert_not_called()


@pytest.mark.asyncio
async def test_failed_event_goes_to_dead_letter(monkeypatch) -> None:
    consumer = ConnectorSyncConsumer()

    processed_repo = AsyncMock()
    processed_repo.is_processed.return_value = False
    processed_repo.mark_processed = AsyncMock()
    monkeypatch.setattr(consumer, "_processed_repo", processed_repo)

    dead_letter_repo = AsyncMock()
    dead_letter_repo.add_failed_event.return_value = {
        "id": "dlq-1",
        "failed_at": "2026-01-01T00:00:00+00:00",
    }
    monkeypatch.setattr(consumer, "_dead_letter_repo", dead_letter_repo)

    monkeypatch.setattr(consumer, "_send_json", AsyncMock())
    monkeypatch.setattr(consumer, "_dead_letter_producer", AsyncMock())

    monkeypatch.setattr(
        consumer,
        "_process_product_changed",
        AsyncMock(side_effect=ValueError("boom")),
    )

    payload = {
        "event_id": "evt-2",
        "event_type": "ProductChanged",
        "source_system": "akeneo",
        "entity_id": "sku-2",
        "product_id": "sku-2",
    }

    with pytest.raises(ValueError):
        await consumer.process_payload(payload)

    dead_letter_repo.add_failed_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_payload_accepts_legacy_event_without_schema_version(monkeypatch) -> None:
    consumer = ConnectorSyncConsumer()

    processed_repo = AsyncMock()
    processed_repo.is_processed.return_value = False
    processed_repo.mark_processed = AsyncMock()
    monkeypatch.setattr(consumer, "_processed_repo", processed_repo)
    monkeypatch.setattr(consumer, "_dead_letter_repo", AsyncMock())
    monkeypatch.setattr(consumer, "_publish_domain_event", AsyncMock())

    process_product_changed = AsyncMock()
    monkeypatch.setattr(consumer, "_process_product_changed", process_product_changed)

    payload = {
        "event_id": "evt-legacy",
        "event_type": "ProductChanged",
        "source_system": "akeneo",
        "entity_id": "sku-legacy",
        "product_id": "sku-legacy",
    }

    await consumer.process_payload(payload)

    process_product_changed.assert_awaited_once()
    processed_repo.mark_processed.assert_awaited_once_with(
        event_id="evt-legacy",
        source_system="akeneo",
        event_type="ProductChanged",
    )


@pytest.mark.asyncio
async def test_ingest_webhook_event_writes_explicit_schema_version(monkeypatch) -> None:
    consumer = ConnectorSyncConsumer()

    monkeypatch.setattr(consumer._settings, "connector_sync_enabled", True)
    monkeypatch.setattr(consumer, "_ingress_producer", AsyncMock())

    send_json = AsyncMock()
    monkeypatch.setattr(consumer, "_send_json", send_json)

    event_id = await consumer.ingest_webhook_event(
        {
            "event_type": "ProductChanged",
            "source_system": "akeneo",
            "entity_id": "sku-1",
            "product_id": "sku-1",
        }
    )

    sent_payload = send_json.await_args.args[1]
    assert sent_payload["schema_version"] == "1.0"
    assert event_id == sent_payload["event_id"]


@pytest.mark.asyncio
async def test_replay_unreplayed_counts_results(monkeypatch) -> None:
    consumer = ConnectorSyncConsumer()

    dead_letter_repo = AsyncMock()
    dead_letter_repo.list_unreplayed.return_value = [{"id": "a"}, {"id": "b"}]
    monkeypatch.setattr(consumer, "_dead_letter_repo", dead_letter_repo)

    monkeypatch.setattr(consumer, "replay_dead_letter", AsyncMock(side_effect=[True, False]))

    result = await consumer.replay_unreplayed(limit=10)

    assert result == {"replayed": 1, "failed": 1}
