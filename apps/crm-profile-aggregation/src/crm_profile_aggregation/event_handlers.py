"""Event handlers for CRM profile aggregation service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_profile_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for profile aggregation subscriptions."""
    logger = configure_logging(app_name="crm-profile-aggregation-events")
    adapters = build_profile_adapters()

    async def handle_user_event(partition_context, event) -> None:  # noqa: ANN001
        await _process_contact_event("user", partition_context, event)

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        await _process_contact_event("order", partition_context, event)

    async def _process_contact_event(scope: str, partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        contact_id = (
            data.get("contact_id")
            or data.get("user_id")
            or data.get("customer_id")
            or data.get("id")
        )
        if not contact_id:
            logger.info(
                "profile_event_skipped",
                event_type=payload.get("event_type"),
                scope=scope,
            )
            return

        context = await adapters.crm.build_contact_context(str(contact_id))
        if context is None:
            logger.info(
                "profile_event_missing_contact",
                event_type=payload.get("event_type"),
                scope=scope,
                contact_id=contact_id,
            )
            return

        summary = await adapters.analytics.summarize_profile(context)
        logger.info(
            "profile_event_processed",
            event_type=payload.get("event_type"),
            scope=scope,
            contact_id=contact_id,
            interaction_count=summary.get("interaction_count"),
            engagement_score=summary.get("engagement_score"),
        )

    return {
        "user-events": handle_user_event,
        "order-events": handle_order_event,
    }
