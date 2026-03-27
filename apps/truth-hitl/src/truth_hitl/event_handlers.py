"""Event handlers for the Truth HITL service."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import HITLAdapters, build_hitl_adapters
from .review_manager import ReviewItem


def build_event_handlers(adapters: HITLAdapters | None = None) -> dict[str, EventHandler]:
    """Build event handlers for hitl-jobs Event Hub subscription."""
    logger = configure_logging(app_name="truth-hitl-events")
    adapters = adapters or build_hitl_adapters()

    async def handle_hitl_job(_partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}

        entity_id = data.get("entity_id")
        attr_id = data.get("attr_id")

        if not entity_id or not attr_id:
            logger.info(
                "hitl_event_skipped event_type=%s reason=missing_entity_id_or_attr_id",
                payload.get("event_type"),
            )
            return

        proposed_at_raw = data.get("proposed_at")
        try:
            proposed_at = (
                datetime.fromisoformat(proposed_at_raw)
                if proposed_at_raw
                else datetime.now(timezone.utc)
            )
        except ValueError:
            proposed_at = datetime.now(timezone.utc)

        item = ReviewItem(
            entity_id=entity_id,
            attr_id=attr_id,
            field_name=data.get("field_name", ""),
            proposed_value=data.get("proposed_value"),
            confidence=float(data.get("confidence", 0.0)),
            current_value=data.get("current_value"),
            source=data.get("source", "ai"),
            proposed_at=proposed_at,
            product_title=data.get("product_title", ""),
            category_label=data.get("category_label", ""),
            status="pending_review",
            original_data=data.get("original_data"),
            enriched_data=data.get("enriched_data"),
            reasoning=data.get("reasoning"),
            source_assets=data.get("source_assets"),
            source_type=data.get("source_type"),
        )

        adapters.review_manager.enqueue(item)
        logger.info(
            "hitl_event_enqueued entity_id=%s attr_id=%s field_name=%s confidence=%.2f",
            entity_id,
            attr_id,
            item.field_name,
            item.confidence,
        )

    return {"hitl-jobs": handle_hitl_job}
