"""Event handlers for CRM support assistance service."""

from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_support_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for support assistance subscriptions."""
    logger = configure_logging(app_name="crm-support-assistance-events")
    adapters = build_support_adapters()

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
            logger.info("support_event_skipped", event_type=payload.get("event_type"))
            return

        context = await adapters.crm.build_contact_context(str(contact_id))
        if context is None:
            logger.info(
                "support_event_missing_contact",
                event_type=payload.get("event_type"),
                contact_id=contact_id,
            )
            return

        issue_summary = data.get("issue_summary") or payload.get("event_type")
        brief = await adapters.assistant.build_support_brief(
            context,
            issue_summary=issue_summary,
        )
        logger.info(
            "support_event_processed",
            event_type=payload.get("event_type"),
            contact_id=contact_id,
            risk=brief.get("risk"),
            next_steps=len(brief.get("next_best_actions", [])),
        )

    return {
        "order-events": handle_order_event,
        "return-events": handle_order_event,
    }
