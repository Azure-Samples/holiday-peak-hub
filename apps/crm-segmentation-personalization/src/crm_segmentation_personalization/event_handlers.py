"""Event handlers for CRM segmentation and personalization service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_segmentation_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for segmentation subscriptions."""
    logger = configure_logging(app_name="crm-segmentation-personalization-events")
    adapters = build_segmentation_adapters()

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        contact_id = (
            data.get("contact_id")
            or data.get("user_id")
            or data.get("customer_id")
            or data.get("id")
        )
        if not contact_id:
            logger.info("segmentation_event_skipped", event_type=payload.get("event_type"))
            return

        context = await adapters.crm.build_contact_context(str(contact_id))
        if context is None:
            logger.info(
                "segmentation_event_missing_contact",
                event_type=payload.get("event_type"),
                contact_id=contact_id,
            )
            return

        segment = await adapters.segmenter.build_segment(context)
        logger.info(
            "segmentation_event_processed",
            event_type=payload.get("event_type"),
            contact_id=contact_id,
            segment=segment.get("segment"),
            preferred_channel=segment.get("personalization", {}).get("preferred_channel"),
        )

    return {"order-events": handle_order_event}
