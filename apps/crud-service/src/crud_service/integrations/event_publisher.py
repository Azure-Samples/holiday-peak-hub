"""Event publisher for Azure Event Hubs."""

import json
import logging
from typing import Any

from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData
from azure.identity.aio import DefaultAzureCredential

from crud_service.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EventPublisher:
    """
    Publishes domain events to Azure Event Hubs using Managed Identity.
    
    Events are published to topic-specific Event Hubs:
    - order-events: OrderCreated, OrderUpdated, OrderCancelled
    - payment-events: PaymentProcessed, PaymentFailed, RefundIssued
    - inventory-events: InventoryReserved, InventoryReleased
    - shipment-events: ShipmentCreated, ShipmentUpdated
    - user-events: UserRegistered, UserUpdated
    """

    def __init__(self):
        self._producers: dict[str, EventHubProducerClient] = {}
        self._credential = None

    async def start(self):
        """Initialize Event Hub producers."""
        logger.info("Starting Event Publisher...")
        self._credential = DefaultAzureCredential()

        # Create producers for each topic
        topics = [
            "order-events",
            "payment-events",
            "inventory-events",
            "shipment-events",
            "user-events",
        ]

        for topic in topics:
            producer = EventHubProducerClient(
                fully_qualified_namespace=settings.event_hub_namespace,
                eventhub_name=topic,
                credential=self._credential,
            )
            self._producers[topic] = producer

        logger.info(f"Event Publisher started with {len(self._producers)} topics")

    async def stop(self):
        """Close all Event Hub producers."""
        logger.info("Stopping Event Publisher...")
        for topic, producer in self._producers.items():
            await producer.close()
            logger.info(f"Closed producer for topic: {topic}")
        self._producers.clear()
        if self._credential:
            await self._credential.close()

    async def publish(self, topic: str, event_type: str, data: dict[str, Any]):
        """
        Publish an event to a specific topic.
        
        Args:
            topic: Event Hub name (e.g., "order-events")
            event_type: Event type (e.g., "OrderCreated")
            data: Event payload
        """
        if topic not in self._producers:
            logger.error(f"Unknown topic: {topic}")
            return

        event_payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": data.get("timestamp"),
        }

        event_data = EventData(json.dumps(event_payload))
        producer = self._producers[topic]

        try:
            async with producer:
                await producer.send_batch([event_data])
            logger.info(f"Published {event_type} to {topic}")
        except Exception as e:
            logger.error(f"Failed to publish {event_type} to {topic}: {e}", exc_info=True)

    # Convenience methods for common events
    async def publish_order_created(self, order: dict):
        """Publish OrderCreated event."""
        await self.publish("order-events", "OrderCreated", order)

    async def publish_payment_processed(self, payment: dict):
        """Publish PaymentProcessed event."""
        await self.publish("payment-events", "PaymentProcessed", payment)

    async def publish_inventory_reserved(self, reservation: dict):
        """Publish InventoryReserved event."""
        await self.publish("inventory-events", "InventoryReserved", reservation)

    async def publish_shipment_created(self, shipment: dict):
        """Publish ShipmentCreated event."""
        await self.publish("shipment-events", "ShipmentCreated", shipment)

    async def publish_user_registered(self, user: dict):
        """Publish UserRegistered event."""
        await self.publish("user-events", "UserRegistered", user)


# Global instance (initialized in lifespan)
_event_publisher: EventPublisher | None = None


def get_event_publisher() -> EventPublisher:
    """Get global event publisher instance."""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher
