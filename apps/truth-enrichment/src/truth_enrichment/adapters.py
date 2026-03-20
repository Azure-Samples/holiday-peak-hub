"""Adapters for the Truth Enrichment service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from holiday_peak_lib.adapters.dam_image_analysis import DAMImageAnalysisAdapter
from holiday_peak_lib.utils.logging import configure_logging

logger = configure_logging(app_name="truth-enrichment")


class ProductStoreAdapter:
    """Read product records from the Cosmos DB truth store."""

    async def get_product(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Return a product dict by entity_id, or None when not found."""
        # In production this calls Cosmos DB; stubbed for local/test use.
        return None

    async def get_schema(self, category: str) -> Optional[dict[str, Any]]:
        """Return a CategorySchema dict for the given category, or None."""
        return None


class ProposedAttributeStoreAdapter:
    """Write proposed attributes to the Cosmos DB `attributes_proposed` container."""

    async def upsert(self, proposed: dict[str, Any]) -> dict[str, Any]:
        """Persist a proposed attribute and return it."""
        logger.info(
            "proposed_attribute_upsert",
            entity_id=proposed.get("entity_id"),
            field_name=proposed.get("field_name"),
            status=proposed.get("status"),
        )
        return proposed

    async def get(self, attribute_id: str) -> Optional[dict[str, Any]]:
        """Return a proposed attribute by id, or None."""
        return None


class TruthAttributeStoreAdapter:
    """Write approved attributes to the Cosmos DB `attributes_truth` container."""

    async def upsert(self, attribute: dict[str, Any]) -> dict[str, Any]:
        """Persist a truth attribute and return it."""
        logger.info(
            "truth_attribute_upsert",
            entity_id=attribute.get("entity_id"),
            field_name=attribute.get("field_name"),
        )
        return attribute


class AuditStoreAdapter:
    """Append audit events to the Cosmos DB `audit_events` container."""

    async def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist an audit event and return it."""
        logger.info(
            "audit_event_appended", action=event.get("action"), entity_id=event.get("entity_id")
        )
        return event


class EventHubPublisher:
    """Publish messages to an Azure Event Hub topic."""

    def __init__(self, topic: str = "hitl-jobs") -> None:
        self.topic = topic
        self._connection_string = os.getenv("EVENT_HUB_CONNECTION_STRING")

    async def publish(self, payload: dict[str, Any]) -> None:
        """Send a message to the configured Event Hub topic."""
        if not self._connection_string:
            logger.info(
                "eventhub_publish_skipped_no_connection",
                topic=self.topic,
                entity_id=payload.get("entity_id"),
            )
            return
        try:
            import json

            from azure.eventhub import EventData
            from azure.eventhub.aio import EventHubProducerClient

            async with EventHubProducerClient.from_connection_string(
                self._connection_string, eventhub_name=self.topic
            ) as producer:
                batch = await producer.create_batch()
                batch.add(EventData(json.dumps(payload)))
                await producer.send_batch(batch)
                logger.info(
                    "eventhub_published", topic=self.topic, entity_id=payload.get("entity_id")
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("eventhub_publish_failed", topic=self.topic, error=str(exc))


@dataclass
class EnrichmentAdapters:
    """Container for all Truth Enrichment service adapters."""

    products: ProductStoreAdapter = field(default_factory=ProductStoreAdapter)
    proposed: ProposedAttributeStoreAdapter = field(default_factory=ProposedAttributeStoreAdapter)
    truth: TruthAttributeStoreAdapter = field(default_factory=TruthAttributeStoreAdapter)
    audit: AuditStoreAdapter = field(default_factory=AuditStoreAdapter)
    image_analysis: DAMImageAnalysisAdapter = field(default_factory=DAMImageAnalysisAdapter)
    hitl_publisher: EventHubPublisher = field(default_factory=EventHubPublisher)


def build_enrichment_adapters() -> EnrichmentAdapters:
    """Construct the default adapter set for the enrichment service."""
    return EnrichmentAdapters()
