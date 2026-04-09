"""Adapters for the Truth HITL service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.self_healing import SelfHealingKernel
from holiday_peak_lib.utils import (
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
)
from holiday_peak_lib.utils.truth_event_hub import (
    TruthEventPublisher,
    build_truth_event_publisher_from_env,
)
from truth_hitl.review_manager import ReviewManager


class EventHubPublisher:
    """Publish approval events to an Azure Event Hub topic."""

    def __init__(
        self,
        topic: str = "export-jobs",
        *,
        publisher: TruthEventPublisher | None = None,
        self_healing_kernel: SelfHealingKernel | None = None,
    ) -> None:
        self.topic = topic
        self._publisher = publisher or build_truth_event_publisher_from_env(
            service_name="truth-hitl",
            namespace_env=PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
            connection_string_env=PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
            self_healing_kernel=self_healing_kernel,
        )

    def attach_self_healing(self, self_healing_kernel: SelfHealingKernel | None) -> None:
        """Attach the shared app kernel after the FastAPI app has bootstrapped."""

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
                "domain": "truth-hitl",
                "entity_id": entity_id,
            },
            remediation_context={
                "preferred_action": "reset_messaging_publisher_bindings",
                "workflow": "approval_fanout",
                "target_topic": self.topic,
            },
        )


def build_hitl_approval_event(
    *,
    entity_id: str,
    approved_fields: list[str],
    reviewer_id: str | None,
    decision_timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Build a canonical export-jobs payload for approved HITL decisions."""
    timestamp = decision_timestamp or datetime.now(timezone.utc)
    return {
        "event_type": "hitl.approved",
        "source": "truth-hitl",
        "data": {
            "entity_id": entity_id,
            "approved_fields": approved_fields,
            "reviewer_id": reviewer_id,
            "decision_timestamp": timestamp.isoformat(),
            "protocol": "pim",
            "status": "approved",
        },
    }


def build_search_enrichment_event(
    *,
    entity_id: str,
    approved_fields: list[str],
    reviewer_id: str | None,
    decision_timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Build a payload for search enrichment refresh after HITL approval."""
    timestamp = decision_timestamp or datetime.now(timezone.utc)
    return {
        "event_type": "hitl.approved.search",
        "source": "truth-hitl",
        "data": {
            "entity_id": entity_id,
            "approved_fields": approved_fields,
            "reviewer_id": reviewer_id,
            "decision_timestamp": timestamp.isoformat(),
            "status": "approved",
        },
    }


@dataclass
class HITLAdapters:
    """Container for Truth HITL service adapters."""

    review_manager: ReviewManager = field(default_factory=ReviewManager)
    export_publisher: EventHubPublisher = field(
        default_factory=lambda: EventHubPublisher("export-jobs")
    )
    search_enrichment_publisher: EventHubPublisher = field(
        default_factory=lambda: EventHubPublisher("search-enrichment-jobs")
    )


def build_hitl_adapters(
    *,
    review_manager: ReviewManager | None = None,
    export_publisher: EventHubPublisher | None = None,
    search_enrichment_publisher: EventHubPublisher | None = None,
) -> HITLAdapters:
    """Create adapters for the HITL review workflow."""
    if review_manager is None and export_publisher is None and search_enrichment_publisher is None:
        shared_default = getattr(build_hitl_adapters, "_shared_default", None)
        if shared_default is None:
            shared_default = HITLAdapters()
            setattr(build_hitl_adapters, "_shared_default", shared_default)
        return shared_default

    return HITLAdapters(
        review_manager=review_manager or ReviewManager(),
        export_publisher=export_publisher or EventHubPublisher("export-jobs"),
        search_enrichment_publisher=search_enrichment_publisher
        or EventHubPublisher("search-enrichment-jobs"),
    )
