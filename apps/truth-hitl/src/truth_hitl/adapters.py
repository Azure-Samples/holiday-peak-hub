"""Adapters for the Truth HITL service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.utils.logging import configure_logging
from truth_hitl.review_manager import ReviewManager

logger = configure_logging(app_name="truth-hitl")


class EventHubPublisher:
    """Publish approval events to an Azure Event Hub topic."""

    def __init__(self, topic: str = "export-jobs") -> None:
        self.topic = topic
        self._connection_string = os.getenv("EVENT_HUB_CONNECTION_STRING")

    async def publish(self, payload: dict[str, Any]) -> None:
        """Send a message to the configured Event Hub topic."""
        if not self._connection_string:
            logger.info(
                "eventhub_publish_skipped_no_connection topic=%s entity_id=%s",
                self.topic,
                payload.get("data", {}).get("entity_id"),
            )
            return

        try:
            from azure.eventhub import EventData
            from azure.eventhub.aio import EventHubProducerClient

            async with EventHubProducerClient.from_connection_string(
                self._connection_string,
                eventhub_name=self.topic,
            ) as producer:
                batch = await producer.create_batch()
                batch.add(EventData(json.dumps(payload)))
                await producer.send_batch(batch)
                logger.info(
                    "eventhub_published topic=%s entity_id=%s",
                    self.topic,
                    payload.get("data", {}).get("entity_id"),
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("eventhub_publish_failed topic=%s error=%s", self.topic, str(exc))


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


@dataclass
class HITLAdapters:
    """Container for Truth HITL service adapters."""

    review_manager: ReviewManager = field(default_factory=ReviewManager)
    export_publisher: EventHubPublisher = field(
        default_factory=lambda: EventHubPublisher("export-jobs")
    )


def build_hitl_adapters(
    *,
    review_manager: ReviewManager | None = None,
    export_publisher: EventHubPublisher | None = None,
) -> HITLAdapters:
    """Create adapters for the HITL review workflow."""
    return HITLAdapters(
        review_manager=review_manager or ReviewManager(),
        export_publisher=export_publisher or EventHubPublisher("export-jobs"),
    )
