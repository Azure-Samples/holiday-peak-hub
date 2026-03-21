"""Unit tests for EventPublisher schema validation."""

from __future__ import annotations

import json

import pytest
from crud_service.integrations.event_publisher import EventPublisher


class _FakeProducer:
    def __init__(self) -> None:
        self.sent: list[list[dict[str, object]]] = []

    async def close(self) -> None:
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_batch(self, events):
        payloads: list[dict[str, object]] = []
        for event in events:
            payloads.append(json.loads(event.body_as_str()))
        self.sent.append(payloads)


@pytest.mark.asyncio
async def test_publish_order_created_validates_and_normalizes_payload() -> None:
    publisher = EventPublisher()
    producer = _FakeProducer()
    publisher._producers = {"order-events": producer}

    await publisher.publish(
        "order-events",
        "OrderCreated",
        {
            "id": "order-1",
            "user_id": "user-1",
            "items": [{"product_id": "sku-1", "quantity": 1, "price": 5.0}],
            "total": 5.0,
            "status": "pending",
            "created_at": "2026-03-21T00:00:00Z",
        },
    )

    assert len(producer.sent) == 1
    payload = producer.sent[0][0]
    assert payload["event_type"] == "OrderCreated"
    assert payload["data"]["order_id"] == "order-1"


@pytest.mark.asyncio
async def test_publish_rejects_mismatched_topic_event_type() -> None:
    publisher = EventPublisher()
    publisher._producers = {"order-events": _FakeProducer()}

    with pytest.raises(ValueError, match="Invalid payload"):
        await publisher.publish(
            "order-events",
            "PaymentProcessed",
            {
                "order_id": "order-1",
                "user_id": "user-1",
            },
        )
