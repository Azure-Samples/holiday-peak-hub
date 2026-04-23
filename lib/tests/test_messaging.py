"""Tests for holiday_peak_lib.messaging module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from holiday_peak_lib.events.versioning import CURRENT_EVENT_SCHEMA_VERSION
from holiday_peak_lib.messaging.async_contract import AgentAsyncContract, TopicDeclaration
from holiday_peak_lib.messaging.contract_endpoint import build_contract_router
from holiday_peak_lib.messaging.topic_subject import TopicSubject
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_topic_registry():
    """Ensure each test starts with an empty TopicSubject registry."""
    TopicSubject.clear_registry()
    yield
    TopicSubject.clear_registry()


# ---------------------------------------------------------------------------
# TopicSubject tests
# ---------------------------------------------------------------------------


class TestTopicSubjectAttachDetach:
    """Handlers can be attached and detached."""

    @pytest.mark.asyncio
    async def test_attach_adds_handler(self) -> None:
        subject = TopicSubject("order-events")
        handler: AsyncMock = AsyncMock()
        subject.attach(handler)
        assert handler in subject.observers

    @pytest.mark.asyncio
    async def test_detach_removes_handler(self) -> None:
        subject = TopicSubject("order-events")
        handler: AsyncMock = AsyncMock()
        subject.attach(handler)
        subject.detach(handler)
        assert handler not in subject.observers

    @pytest.mark.asyncio
    async def test_detach_missing_handler_is_noop(self) -> None:
        subject = TopicSubject("order-events")
        handler: AsyncMock = AsyncMock()
        subject.detach(handler)  # should not raise
        assert subject.observers == []


class TestTopicSubjectNotify:
    """notify invokes all attached async handlers."""

    @pytest.mark.asyncio
    async def test_notify_calls_handlers(self) -> None:
        subject = TopicSubject("inventory-events")
        handler_a: AsyncMock = AsyncMock()
        handler_b: AsyncMock = AsyncMock()
        subject.attach(handler_a)
        subject.attach(handler_b)

        payload: dict[str, Any] = {"item": "SKU-123", "qty": 5}
        await subject.notify(payload)

        handler_a.assert_awaited_once_with(payload)
        handler_b.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_notify_with_no_handlers(self) -> None:
        subject = TopicSubject("payment-events")
        await subject.notify({"amount": 10.0})  # should not raise


class TestTopicSubjectPublish:
    """publish delegates to the provided publisher."""

    @pytest.mark.asyncio
    async def test_publish_delegates_to_publisher(self) -> None:
        subject = TopicSubject("shipment-events")
        publisher = AsyncMock()
        publisher.send = AsyncMock()

        payload: dict[str, Any] = {"tracking": "TRK-001"}
        await subject.publish(payload, publisher=publisher)

        publisher.send.assert_awaited_once_with("shipment-events", payload)

    @pytest.mark.asyncio
    async def test_publish_custom_event_hub_name(self) -> None:
        subject = TopicSubject("product-events", event_hub_name="custom-hub")
        publisher = AsyncMock()
        publisher.send = AsyncMock()

        payload: dict[str, Any] = {"sku": "ABC"}
        await subject.publish(payload, publisher=publisher)

        publisher.send.assert_awaited_once_with("custom-hub", payload)

    @pytest.mark.asyncio
    async def test_publish_without_publisher_still_notifies(self) -> None:
        subject = TopicSubject("order-events")
        handler: AsyncMock = AsyncMock()
        subject.attach(handler)

        payload: dict[str, Any] = {"order_id": "O-1"}
        await subject.publish(payload)

        handler.assert_awaited_once_with(payload)


class TestTopicSubjectRegistry:
    """get_all_topics returns registered topics."""

    def test_registry_tracks_instances(self) -> None:
        s1 = TopicSubject("topic-a")
        s2 = TopicSubject("topic-b")
        registry = TopicSubject.get_all_topics()
        assert registry["topic-a"] is s1
        assert registry["topic-b"] is s2

    def test_clear_registry(self) -> None:
        TopicSubject("topic-x")
        TopicSubject.clear_registry()
        assert TopicSubject.get_all_topics() == {}


class TestTopicSubjectDuplicateAttach:
    """Attaching the same handler twice is idempotent."""

    @pytest.mark.asyncio
    async def test_duplicate_attach_is_idempotent(self) -> None:
        subject = TopicSubject("user-events")
        handler: AsyncMock = AsyncMock()
        subject.attach(handler)
        subject.attach(handler)
        assert subject.observers.count(handler) == 1

        await subject.notify({"user_id": "U-1"})
        handler.assert_awaited_once()


# ---------------------------------------------------------------------------
# AgentAsyncContract tests
# ---------------------------------------------------------------------------


class TestAgentAsyncContract:
    """Contract model serialization and validation."""

    def test_contract_serialization(self) -> None:
        contract = AgentAsyncContract(
            service_name="inventory-agent",
            publishes=[
                TopicDeclaration(
                    topic="inventory-events",
                    event_types=["InventoryReserved", "InventoryReleased"],
                    description="Inventory mutations",
                ),
            ],
            consumes=[
                TopicDeclaration(
                    topic="order-events",
                    event_types=["OrderCreated"],
                ),
            ],
        )
        data = contract.model_dump()
        roundtrip = AgentAsyncContract.model_validate(data)
        assert roundtrip == contract

    def test_contract_with_empty_topics(self) -> None:
        contract = AgentAsyncContract(service_name="empty-agent")
        data = contract.model_dump()
        assert data["publishes"] == []
        assert data["consumes"] == []
        assert data["version"] == CURRENT_EVENT_SCHEMA_VERSION

    def test_contract_with_multiple_topics(self) -> None:
        contract = AgentAsyncContract(
            service_name="multi-agent",
            publishes=[
                TopicDeclaration(topic="order-events", event_types=["OrderCreated"]),
                TopicDeclaration(topic="payment-events", event_types=["PaymentProcessed"]),
            ],
            consumes=[
                TopicDeclaration(topic="inventory-events", event_types=["InventoryUpdated"]),
                TopicDeclaration(topic="shipment-events", event_types=["ShipmentCreated"]),
                TopicDeclaration(topic="return-events", event_types=["ReturnRequested"]),
            ],
        )
        assert len(contract.publishes) == 2
        assert len(contract.consumes) == 3


# ---------------------------------------------------------------------------
# Contract endpoint tests
# ---------------------------------------------------------------------------


class TestContractEndpoint:
    """FastAPI router serves the contract at GET /async/contract."""

    @pytest.fixture
    def contract(self) -> AgentAsyncContract:
        return AgentAsyncContract(
            service_name="test-agent",
            publishes=[
                TopicDeclaration(
                    topic="order-events",
                    event_types=["OrderCreated"],
                    description="Order lifecycle",
                ),
            ],
        )

    @pytest.fixture
    def app(self, contract: AgentAsyncContract) -> FastAPI:
        app = FastAPI()
        app.include_router(build_contract_router(contract))
        return app

    @pytest.mark.asyncio
    async def test_contract_endpoint_returns_json(self, app: FastAPI) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/async/contract")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_contract_endpoint_content(
        self,
        app: FastAPI,
        contract: AgentAsyncContract,
    ) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/async/contract")
        body = response.json()
        assert body["service_name"] == contract.service_name
        assert body["version"] == contract.version
        assert len(body["publishes"]) == 1
        assert body["publishes"][0]["topic"] == "order-events"
