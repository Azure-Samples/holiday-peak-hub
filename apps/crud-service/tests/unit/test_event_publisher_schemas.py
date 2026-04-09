"""Unit tests for EventPublisher schema validation."""

from __future__ import annotations

import json

import pytest
from crud_service.integrations.event_publisher import EventPublisher
from holiday_peak_lib.events import CURRENT_EVENT_SCHEMA_VERSION
from holiday_peak_lib.self_healing import SelfHealingKernel, default_surface_manifest
from holiday_peak_lib.utils import CompensationResult
from holiday_peak_lib.utils.event_hub import EventPublishError


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


def _set_producers(publisher: object, producers: dict[str, _FakeProducer]) -> None:
    publisher_dict = getattr(publisher, "__dict__")
    publisher_dict["_producers"] = producers


def _set_self_healing_kernel(
    publisher: object,
    kernel: SelfHealingKernel,
) -> None:
    publisher_dict = getattr(publisher, "__dict__")
    publisher_dict["_self_healing_kernel"] = kernel


@pytest.mark.asyncio
async def test_publish_order_created_validates_and_normalizes_payload() -> None:
    publisher = EventPublisher()
    producer = _FakeProducer()
    _set_producers(publisher, {"order-events": producer})

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
    assert payload["schema_version"] == CURRENT_EVENT_SCHEMA_VERSION
    assert payload["event_type"] == "OrderCreated"
    assert payload["data"]["order_id"] == "order-1"


@pytest.mark.asyncio
async def test_publish_rejects_mismatched_topic_event_type() -> None:
    publisher = EventPublisher()
    _set_producers(publisher, {"order-events": _FakeProducer()})

    with pytest.raises(EventPublishError) as exc_info:
        await publisher.publish(
            "order-events",
            "PaymentProcessed",
            {
                "order_id": "order-1",
                "user_id": "user-1",
            },
        )

    assert exc_info.value.envelope.category.value == "payload_validation"


@pytest.mark.asyncio
async def test_publish_product_updated_validates_product_event_payload() -> None:
    publisher = EventPublisher()
    producer = _FakeProducer()
    _set_producers(publisher, {"product-events": producer})

    await publisher.publish(
        "product-events",
        "ProductUpdated",
        {
            "id": "sku-1",
            "name": "Widget",
            "category_id": "cat-1",
            "price": 12.5,
            "timestamp": "2026-03-21T00:00:00Z",
        },
    )

    assert len(producer.sent) == 1
    payload = producer.sent[0][0]
    assert payload["schema_version"] == CURRENT_EVENT_SCHEMA_VERSION
    assert payload["event_type"] == "ProductUpdated"
    assert payload["data"]["product_id"] == "sku-1"
    assert payload["data"]["sku"] == "sku-1"


@pytest.mark.asyncio
async def test_publish_user_updated_uses_canonical_retail_envelope() -> None:
    publisher = EventPublisher()
    producer = _FakeProducer()
    _set_producers(publisher, {"user-events": producer})

    await publisher.publish(
        "user-events",
        "UserUpdated",
        {
            "id": "user-1",
            "email": "user@example.com",
            "name": "Updated User",
            "timestamp": "2026-03-21T00:00:00Z",
        },
    )

    assert len(producer.sent) == 1
    payload = producer.sent[0][0]
    assert payload["schema_version"] == CURRENT_EVENT_SCHEMA_VERSION
    assert payload["data"]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_publish_failure_raises_and_records_compensation_metadata() -> None:
    publisher = EventPublisher()
    kernel = SelfHealingKernel(
        service_name="crud-service",
        manifest=default_surface_manifest("crud-service"),
        enabled=True,
        reconcile_on_messaging_error=True,
    )
    _set_self_healing_kernel(
        publisher,
        kernel,
    )
    producer = _FakeProducer()

    async def _failing_send(_events):
        raise TimeoutError("event hub unavailable")

    producer.send_batch = _failing_send
    _set_producers(publisher, {"order-events": producer})

    with pytest.raises(EventPublishError):
        await publisher.publish_order_created(
            {
                "id": "order-2",
                "user_id": "user-2",
                "items": [{"product_id": "sku-2", "quantity": 1, "price": 8.0}],
                "total": 8.0,
                "status": "pending",
                "created_at": "2026-03-21T00:00:00Z",
            },
            remediation_context={"workflow": "checkout_finalize"},
            compensation_result=CompensationResult(completed=["order_write_rollback"]),
        )

    incident = kernel.list_incidents(limit=1)[0]
    assert incident.metadata["domain"] == "order"
    assert incident.metadata["compensation"]["completed_actions"] == ["order_write_rollback"]
    assert incident.actions == ["reset_messaging_publisher_bindings"]
