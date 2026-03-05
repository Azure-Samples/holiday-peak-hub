"""Event-driven connector synchronization consumer."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import uuid4

from azure.core.exceptions import AzureError
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from crud_service.config.settings import get_settings
from crud_service.repositories import OrderRepository, ProductRepository, UserRepository
from crud_service.repositories.connector_sync import (
    DeadLetterConnectorEventRepository,
    ProcessedConnectorEventRepository,
)
from holiday_peak_lib.events import (
    CustomerUpdated,
    InventoryUpdated,
    OrderStatusChanged,
    PriceUpdated,
    ProductChanged,
    parse_connector_event,
)
from opentelemetry import trace

logger = logging.getLogger(__name__)


class ConnectorSyncConsumer:
    """Consumes connector sync events and updates CRUD local state."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._credential: DefaultAzureCredential | None = None
        self._consumer: EventHubConsumerClient | None = None
        self._ingress_producer: EventHubProducerClient | None = None
        self._dead_letter_producer: EventHubProducerClient | None = None
        self._domain_producer: EventHubProducerClient | None = None
        self._consumer_task: asyncio.Task | None = None

        self._processed_repo = ProcessedConnectorEventRepository()
        self._dead_letter_repo = DeadLetterConnectorEventRepository()
        self._product_repo = ProductRepository()
        self._user_repo = UserRepository()
        self._order_repo = OrderRepository()
        self._tracer = trace.get_tracer(__name__)

    async def start(self) -> None:
        """Start background connector event consumption."""

        if not self._settings.connector_sync_enabled:
            logger.info("connector_sync_disabled")
            return

        self._credential = DefaultAzureCredential()

        self._consumer = EventHubConsumerClient(
            fully_qualified_namespace=self._settings.event_hub_namespace,
            eventhub_name=self._settings.connector_sync_ingress_eventhub,
            consumer_group=self._settings.connector_sync_consumer_group,
            credential=self._credential,
        )
        self._ingress_producer = EventHubProducerClient(
            fully_qualified_namespace=self._settings.event_hub_namespace,
            eventhub_name=self._settings.connector_sync_ingress_eventhub,
            credential=self._credential,
        )
        self._dead_letter_producer = EventHubProducerClient(
            fully_qualified_namespace=self._settings.event_hub_namespace,
            eventhub_name=self._settings.connector_sync_deadletter_eventhub,
            credential=self._credential,
        )
        self._domain_producer = EventHubProducerClient(
            fully_qualified_namespace=self._settings.event_hub_namespace,
            eventhub_name=self._settings.connector_sync_domain_eventhub,
            credential=self._credential,
        )

        self._consumer_task = asyncio.create_task(self._run_consumer())
        logger.info(
            "connector_sync_started ingress_hub=%s consumer_group=%s",
            self._settings.connector_sync_ingress_eventhub,
            self._settings.connector_sync_consumer_group,
        )

    async def stop(self) -> None:
        """Stop consumer and close clients."""

        if self._consumer_task:
            self._consumer_task.cancel()
            await asyncio.gather(self._consumer_task, return_exceptions=True)
            self._consumer_task = None

        for client in (
            self._consumer,
            self._ingress_producer,
            self._dead_letter_producer,
            self._domain_producer,
        ):
            if client:
                await client.close()

        self._consumer = None
        self._ingress_producer = None
        self._dead_letter_producer = None
        self._domain_producer = None

        if self._credential:
            await self._credential.close()
            self._credential = None

        logger.info("connector_sync_stopped")

    async def ingest_webhook_event(self, payload: dict[str, Any]) -> str:
        """Publish a webhook payload to the connector ingress Event Hub."""

        if not self._settings.connector_sync_enabled:
            raise RuntimeError("Connector sync is disabled")
        if not self._ingress_producer:
            raise RuntimeError("Connector sync producer is not initialized")

        envelope = dict(payload)
        envelope.setdefault("event_id", str(uuid4()))
        envelope.setdefault("occurred_at", datetime.now(UTC).isoformat())

        await self._send_json(self._ingress_producer, envelope)
        return str(envelope["event_id"])

    async def replay_dead_letter(self, dead_letter_id: str) -> bool:
        """Replay a single dead-letter event by identifier."""

        item = await self._dead_letter_repo.get_by_id(dead_letter_id)
        if not item:
            return False

        payload = item.get("event_payload")
        if not isinstance(payload, dict):
            return False

        await self.process_payload(payload)
        await self._dead_letter_repo.mark_replayed(dead_letter_id)
        return True

    async def replay_unreplayed(self, limit: int = 100) -> dict[str, int]:
        """Replay pending dead-letter events."""

        events = await self._dead_letter_repo.list_unreplayed(limit=limit)
        replayed = 0
        failed = 0
        for item in events:
            ok = await self.replay_dead_letter(str(item["id"]))
            if ok:
                replayed += 1
            else:
                failed += 1
        return {"replayed": replayed, "failed": failed}

    async def _run_consumer(self) -> None:
        """Background receive loop for connector events."""

        assert self._consumer is not None

        async def on_event(partition_context, event):  # noqa: ANN001
            payload = json.loads(event.body_as_str())
            await self.process_payload(payload)
            await partition_context.update_checkpoint(event)

        async def on_error(partition_context, error):  # noqa: ANN001
            logger.error(
                "connector_sync_consumer_error partition=%s error=%s", partition_context, error
            )

        try:
            async with self._consumer:
                await self._consumer.receive(
                    on_event=on_event,
                    on_error=on_error,
                    starting_position=self._settings.connector_sync_starting_position,
                )
        except asyncio.CancelledError:
            logger.info("connector_sync_consumer_cancelled")
        except (AzureError, RuntimeError, ValueError, OSError) as exc:
            logger.error("connector_sync_consumer_stopped error=%s", exc, exc_info=True)

    async def process_payload(self, payload: dict[str, Any]) -> None:
        """Process one connector event payload with idempotency and DLQ."""

        with self._tracer.start_as_current_span("connector_sync.process_event") as span:
            span.set_attribute("connector.event_type", payload.get("event_type", "unknown"))
            span.set_attribute("connector.source_system", payload.get("source_system", "unknown"))

            try:
                event = parse_connector_event(payload)
            except Exception as exc:  # noqa: BLE001
                await self._send_to_dead_letter(payload, f"schema_validation_failed: {exc}")
                raise

            if await self._processed_repo.is_processed(event.event_id, event.source_system):
                logger.info(
                    "connector_sync_duplicate_ignored event_id=%s source=%s",
                    event.event_id,
                    event.source_system,
                )
                return

            processor = self._resolve_processor(event.event_type)
            try:
                await processor(event)
                await self._processed_repo.mark_processed(
                    event_id=event.event_id,
                    source_system=event.source_system,
                    event_type=event.event_type,
                )
                await self._publish_domain_event(event)
            except Exception as exc:  # noqa: BLE001
                await self._send_to_dead_letter(payload, str(exc))
                raise

    def _resolve_processor(self, event_type: str) -> Callable[[Any], Any]:
        processors: dict[str, Callable[[Any], Any]] = {
            "ProductChanged": self._process_product_changed,
            "InventoryUpdated": self._process_inventory_updated,
            "CustomerUpdated": self._process_customer_updated,
            "OrderStatusChanged": self._process_order_status_changed,
            "PriceUpdated": self._process_price_updated,
        }
        if event_type not in processors:
            raise ValueError(f"Unsupported connector event type: {event_type}")
        return processors[event_type]

    async def _process_product_changed(self, event: ProductChanged) -> None:
        product = await self._product_repo.get_by_id(event.product_id)
        updated = product or {"id": event.product_id}

        if event.name is not None:
            updated["name"] = event.name
        if event.description is not None:
            updated["description"] = event.description
        if event.category_id is not None:
            updated["category_id"] = event.category_id
        if event.image_url is not None:
            updated["image_url"] = event.image_url

        if event.attributes:
            existing = updated.get("attributes") or {}
            existing.update(event.attributes)
            updated["attributes"] = existing

        await self._product_repo.update(updated)

    async def _process_inventory_updated(self, event: InventoryUpdated) -> None:
        product = await self._product_repo.get_by_id(event.product_id)
        if not product:
            product = {
                "id": event.product_id,
                "name": event.product_id,
                "description": "",
                "price": 0.0,
                "category_id": "unassigned",
            }

        inventory = product.get("inventory") or {}
        inventory["quantity"] = event.quantity
        if event.location_id:
            inventory["location_id"] = event.location_id
        if event.available is not None:
            inventory["available"] = event.available
        else:
            inventory["available"] = event.quantity > 0

        product["inventory"] = inventory
        product["in_stock"] = bool(inventory["available"])
        await self._product_repo.update(product)

    async def _process_customer_updated(self, event: CustomerUpdated) -> None:
        customer = await self._user_repo.get_by_id(event.customer_id)
        updated = customer or {
            "id": event.customer_id,
            "created_at": datetime.now(UTC).isoformat(),
        }

        if event.email is not None:
            updated["email"] = event.email
        if event.name is not None:
            updated["name"] = event.name
        if event.phone is not None:
            updated["phone"] = event.phone
        if event.loyalty_tier is not None:
            updated["loyalty_tier"] = event.loyalty_tier
        if event.profile:
            profile = updated.get("profile") or {}
            profile.update(event.profile)
            updated["profile"] = profile

        await self._user_repo.update(updated)

    async def _process_order_status_changed(self, event: OrderStatusChanged) -> None:
        order = await self._order_repo.get_by_id(event.order_id)
        if not order:
            raise ValueError(f"Order not found for status update: {event.order_id}")

        order["status"] = event.status
        if event.status_reason:
            order["status_reason"] = event.status_reason
        if event.tracking_id:
            order["tracking_id"] = event.tracking_id

        await self._order_repo.update(order)

    async def _process_price_updated(self, event: PriceUpdated) -> None:
        product = await self._product_repo.get_by_id(event.product_id)
        if not product:
            raise ValueError(f"Product not found for price update: {event.product_id}")

        product["price"] = event.price
        product["currency"] = event.currency
        if event.effective_from:
            product["price_effective_from"] = event.effective_from.isoformat()

        await self._product_repo.update(product)

    async def _publish_domain_event(self, event: Any) -> None:
        if not self._domain_producer:
            return

        domain_event = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source_system": event.source_system,
            "entity_id": event.entity_id,
            "tenant_id": event.tenant_id,
            "occurred_at": event.occurred_at.isoformat(),
            "data": event.model_dump(mode="json"),
        }
        await self._send_json(self._domain_producer, domain_event)

    async def _send_to_dead_letter(self, payload: dict[str, Any], error: str) -> None:
        failed = await self._dead_letter_repo.add_failed_event(event_payload=payload, error=error)

        if self._dead_letter_producer:
            dead_letter_event = {
                "dead_letter_id": failed["id"],
                "error": error,
                "event_payload": payload,
                "failed_at": failed["failed_at"],
            }
            await self._send_json(self._dead_letter_producer, dead_letter_event)

        logger.error(
            "connector_sync_dead_lettered dead_letter_id=%s error=%s",
            failed["id"],
            error,
        )

    @staticmethod
    async def _send_json(producer: EventHubProducerClient, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload)
        batch = await producer.create_batch()
        batch.add(EventData(serialized))
        await producer.send_batch(batch)


@lru_cache
def get_connector_sync_consumer() -> ConnectorSyncConsumer:
    """Get global connector synchronization consumer singleton."""

    return ConnectorSyncConsumer()
