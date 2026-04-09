"""Adapters for the Truth Enrichment service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from holiday_peak_lib.adapters.dam_image_analysis import DAMImageAnalysisAdapter
from holiday_peak_lib.self_healing import SelfHealingKernel
from holiday_peak_lib.utils import (
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
)
from holiday_peak_lib.utils.logging import configure_logging
from holiday_peak_lib.utils.truth_event_hub import (
    TruthEventPublisher,
    build_truth_event_publisher_from_env,
)

logger = configure_logging(app_name="truth-enrichment")


class ProductStoreAdapter:
    """Read product records from the Cosmos DB truth store."""

    async def get_product(self, _entity_id: str) -> Optional[dict[str, Any]]:
        """Return a product dict by entity_id, or None when not found."""
        # In production this calls Cosmos DB; stubbed for local/test use.
        return None

    async def get_schema(self, _category: str) -> Optional[dict[str, Any]]:
        """Return a CategorySchema dict for the given category, or None."""
        return None


class ProposedAttributeStoreAdapter:
    """Write proposed attributes to the Cosmos DB `attributes_proposed` container."""

    async def upsert(self, proposed: dict[str, Any]) -> dict[str, Any]:
        """Persist a proposed attribute and return it."""
        logger.info(
            "proposed_attribute_upsert entity_id=%s field_name=%s status=%s",
            proposed.get("entity_id"),
            proposed.get("field_name"),
            proposed.get("status"),
        )
        return proposed

    async def get(self, _attribute_id: str) -> Optional[dict[str, Any]]:
        """Return a proposed attribute by id, or None."""
        return None


class TruthAttributeStoreAdapter:
    """Write approved attributes to the Cosmos DB `attributes_truth` container."""

    async def upsert(self, attribute: dict[str, Any]) -> dict[str, Any]:
        """Persist a truth attribute and return it."""
        logger.info(
            "truth_attribute_upsert entity_id=%s field_name=%s",
            attribute.get("entity_id"),
            attribute.get("field_name"),
        )
        return attribute


class AuditStoreAdapter:
    """Append audit events to the Cosmos DB `audit_events` container."""

    async def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Persist an audit event and return it."""
        logger.info(
            "audit_event_appended action=%s entity_id=%s",
            event.get("action"),
            event.get("entity_id"),
        )
        return event


class EventHubPublisher:
    """Publish messages to an Azure Event Hub topic."""

    def __init__(
        self,
        topic: str = "hitl-jobs",
        *,
        publisher: TruthEventPublisher | None = None,
        self_healing_kernel: SelfHealingKernel | None = None,
    ) -> None:
        self.topic = topic
        self._publisher = publisher or build_truth_event_publisher_from_env(
            service_name="truth-enrichment",
            namespace_env=PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
            connection_string_env=PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
            self_healing_kernel=self_healing_kernel,
        )

    def attach_self_healing(self, self_healing_kernel: SelfHealingKernel | None) -> None:
        """Attach the app-owned self-healing kernel after bootstrap."""

        if hasattr(self._publisher, "self_healing_kernel"):
            self._publisher.self_healing_kernel = self_healing_kernel

    async def publish(self, payload: dict[str, Any]) -> None:
        """Send a message to the configured Event Hub topic."""
        payload_data = payload.get("data")
        data: dict[str, Any] = payload_data if isinstance(payload_data, dict) else {}
        entity_id = payload.get("entity_id") or data.get("entity_id")
        await self._publisher.publish_payload(
            self.topic,
            payload,
            metadata={
                "domain": "truth-enrichment",
                "entity_id": entity_id,
            },
            remediation_context={
                "preferred_action": "reset_messaging_publisher_bindings",
                "workflow": "hitl_review_dispatch",
                "target_topic": self.topic,
            },
        )


@dataclass
class EnrichmentAdapters:
    """Container for all Truth Enrichment service adapters."""

    products: ProductStoreAdapter = field(default_factory=ProductStoreAdapter)
    proposed: ProposedAttributeStoreAdapter = field(default_factory=ProposedAttributeStoreAdapter)
    truth: TruthAttributeStoreAdapter = field(default_factory=TruthAttributeStoreAdapter)
    audit: AuditStoreAdapter = field(default_factory=AuditStoreAdapter)
    dam: DAMImageAnalysisAdapter = field(default_factory=DAMImageAnalysisAdapter)
    image_analysis: DAMImageAnalysisAdapter | None = None
    hitl_publisher: EventHubPublisher = field(default_factory=EventHubPublisher)

    def __post_init__(self) -> None:
        if self.image_analysis is not None:
            self.dam = self.image_analysis
        self.image_analysis = self.dam


def build_enrichment_adapters() -> EnrichmentAdapters:
    """Construct the default adapter set for the enrichment service."""
    max_images_raw = os.getenv("DAM_MAX_IMAGES", "4")
    try:
        max_images = max(1, int(max_images_raw))
    except ValueError:
        max_images = 4

    return EnrichmentAdapters(dam=DAMImageAnalysisAdapter(max_images=max_images))
