"""Event publisher for Azure Event Hubs."""

import json
import logging
from functools import lru_cache
from typing import Any

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from crud_service.config import get_settings
from holiday_peak_lib.events import RETAIL_EVENT_TOPICS, build_retail_event_payload
from holiday_peak_lib.self_healing import SelfHealingKernel
from holiday_peak_lib.utils import CompensationResult, get_correlation_id
from holiday_peak_lib.utils.event_hub import (
    CRITICAL_SAGA_PUBLISH_PROFILE,
    DeadLetterCallback,
    TerminalFailureHandler,
    build_publish_failure_envelope,
    emit_publish_failure,
    publish_with_reliability,
    resolve_publish_reliability_profile,
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)
settings = get_settings()


class EventPublisher:
    """
    Publishes domain events to Azure Event Hubs using Managed Identity.

    Events are published to topic-specific Event Hubs:
    - order-events: OrderCreated, OrderUpdated, OrderCancelled
    - payment-events: PaymentProcessed, PaymentFailed, RefundIssued
    - return-events: ReturnRequested, ReturnApproved, ReturnRejected, ReturnReceived, ReturnRestocked, ReturnRefunded
    - inventory-events: InventoryReserved, InventoryReleased
    - shipment-events: ShipmentCreated, ShipmentUpdated
    - product-events: ProductCreated, ProductUpdated, ProductDeleted
    - user-events: UserRegistered, UserUpdated
    """

    def __init__(self):
        self._producers: dict[str, EventHubProducerClient] = {}
        self._credential = None
        self._self_healing_kernel = SelfHealingKernel.from_env(settings.service_name)
        self._topic_profiles = {
            topic: CRITICAL_SAGA_PUBLISH_PROFILE
            for topic in (
                "order-events",
                "payment-events",
                "return-events",
                "inventory-events",
                "shipment-events",
                "product-events",
                "user-events",
            )
        }

    @staticmethod
    def _extract_entity_id(data: dict[str, Any]) -> Any | None:
        for key in (
            "id",
            "order_id",
            "payment_id",
            "return_id",
            "reservation_id",
            "shipment_id",
            "product_id",
            "user_id",
            "sku",
        ):
            value = data.get(key)
            if value is not None:
                return value
        return None

    def _build_publish_metadata(
        self,
        *,
        topic: str,
        event_type: str,
        data: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        raw_payload_data = event_payload.get("data")
        payload_data: dict[str, Any] = (
            raw_payload_data if isinstance(raw_payload_data, dict) else {}
        )
        metadata = {
            "domain": topic.removesuffix("-events"),
            "topic": topic,
            "event_type": event_type,
            "entity_id": self._extract_entity_id(payload_data or data),
            "tenant_id": payload_data.get("tenant_id") or data.get("tenant_id"),
            "correlation_id": get_correlation_id(),
        }
        return {key: value for key, value in metadata.items() if value is not None}

    async def start(self):
        """Initialize Event Hub producers."""
        logger.info("Starting Event Publisher...")
        self._credential = DefaultAzureCredential()

        # Create producers for each topic
        topics = [
            "order-events",
            "payment-events",
            "return-events",
            "inventory-events",
            "shipment-events",
            "product-events",
            "user-events",
        ]

        for topic in topics:
            producer = EventHubProducerClient(
                fully_qualified_namespace=settings.event_hub_namespace,
                eventhub_name=topic,
                credential=self._credential,
            )
            self._producers[topic] = producer

        logger.info("Event Publisher started with %d topics", len(self._producers))

    async def stop(self):
        """Close all Event Hub producers."""
        logger.info("Stopping Event Publisher...")
        for topic, producer in self._producers.items():
            await producer.close()
            logger.info("Closed producer for topic: %s", topic)
        self._producers.clear()
        if self._credential:
            await self._credential.close()

    async def publish(
        self,
        topic: str,
        event_type: str,
        data: dict[str, Any],
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """
        Publish an event to a specific topic.

        Args:
            topic: Event Hub name (e.g., "order-events")
            event_type: Event type (e.g., "OrderCreated")
            data: Event payload
        """
        await self._publish_internal(
            topic,
            event_type,
            data,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def _publish_internal(
        self,
        topic: str,
        event_type: str,
        data: dict[str, Any],
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ) -> None:
        profile = resolve_publish_reliability_profile(
            topic,
            topic_profiles=self._topic_profiles,
            default_profile=CRITICAL_SAGA_PUBLISH_PROFILE,
        )

        try:
            if topic in RETAIL_EVENT_TOPICS:
                event_payload = build_retail_event_payload(
                    topic=topic,
                    event_type=event_type,
                    data=data,
                )
            else:
                event_payload = {
                    "event_type": event_type,
                    "data": data,
                    "timestamp": data.get("timestamp"),
                }
        except (ValidationError, ValueError) as exc:
            envelope = build_publish_failure_envelope(
                error=exc,
                service_name=settings.service_name,
                topic=topic,
                event_type=event_type,
                profile=profile,
                metadata={
                    "domain": topic.removesuffix("-events"),
                    "correlation_id": get_correlation_id(),
                },
                remediation_context=remediation_context,
                compensation_result=compensation_result,
            )
            publish_error = await emit_publish_failure(
                envelope,
                self_healing_kernel=self._self_healing_kernel,
                logger=logger,
            )
            raise publish_error from exc

        event_data = EventData(json.dumps(event_payload))

        async def _send() -> None:
            producer = self._producers[topic]
            async with producer:
                await producer.send_batch([event_data])

        await publish_with_reliability(
            send=_send,
            service_name=settings.service_name,
            topic=topic,
            event_type=event_type,
            profile=profile,
            self_healing_kernel=self._self_healing_kernel,
            logger=logger,
            metadata=self._build_publish_metadata(
                topic=topic,
                event_type=event_type,
                data=data,
                event_payload=event_payload,
            ),
            remediation_context={
                "preferred_action": profile.remediation_action,
                "workflow": "crud_domain_event_publish",
                "target_topic": topic,
                **(remediation_context or {}),
            },
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

        logger.info("Published %s to %s", event_type, topic)

    # Convenience methods for common events
    async def publish_order_created(
        self,
        order: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish OrderCreated event."""
        await self._publish_internal(
            "order-events",
            "OrderCreated",
            order,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_payment_processed(
        self,
        payment: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish PaymentProcessed event."""
        await self._publish_internal(
            "payment-events",
            "PaymentProcessed",
            payment,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_inventory_reserved(
        self,
        reservation: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish InventoryReserved event."""
        await self._publish_internal(
            "inventory-events",
            "InventoryReserved",
            reservation,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_shipment_created(
        self,
        shipment: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish ShipmentCreated event."""
        await self._publish_internal(
            "shipment-events",
            "ShipmentCreated",
            shipment,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_user_registered(
        self,
        user: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish UserRegistered event."""
        await self._publish_internal(
            "user-events",
            "UserRegistered",
            user,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_product_updated(
        self,
        product: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish ProductUpdated event."""
        await self._publish_internal(
            "product-events",
            "ProductUpdated",
            product,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_return_lifecycle_event(
        self,
        *,
        event_type: str,
        data: dict,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish return lifecycle events to return-events topic."""
        await self._publish_internal(
            "return-events",
            event_type,
            data,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )

    async def publish_refund_issued(
        self,
        refund: dict,
        *,
        remediation_context: dict[str, Any] | None = None,
        compensation_result: CompensationResult | None = None,
        on_terminal_failure: TerminalFailureHandler | None = None,
        dead_letter_callback: DeadLetterCallback | None = None,
    ):
        """Publish RefundIssued event to payment-events topic."""
        await self._publish_internal(
            "payment-events",
            "RefundIssued",
            refund,
            remediation_context=remediation_context,
            compensation_result=compensation_result,
            on_terminal_failure=on_terminal_failure,
            dead_letter_callback=dead_letter_callback,
        )


@lru_cache(maxsize=1)
def get_event_publisher() -> EventPublisher:
    """Get global event publisher instance."""
    return EventPublisher()
