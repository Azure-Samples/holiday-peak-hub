"""Event handlers for CRM campaign intelligence service."""
from __future__ import annotations

import json

from holiday_peak_lib.utils.event_hub import EventHandler
from holiday_peak_lib.utils.logging import configure_logging

from .adapters import build_campaign_adapters


def build_event_handlers() -> dict[str, EventHandler]:
    """Build event handlers for campaign intelligence subscriptions."""
    logger = configure_logging(app_name="crm-campaign-intelligence-events")
    adapters = build_campaign_adapters()

    async def handle_user_event(partition_context, event) -> None:  # noqa: ANN001
        await _process_campaign_event("user", partition_context, event)

    async def handle_order_event(partition_context, event) -> None:  # noqa: ANN001
        await _process_campaign_event("order", partition_context, event)

    async def handle_payment_event(partition_context, event) -> None:  # noqa: ANN001
        await _process_campaign_event("payment", partition_context, event)

    async def _process_campaign_event(scope: str, partition_context, event) -> None:  # noqa: ANN001
        payload = json.loads(event.body_as_str())
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        campaign_id = data.get("campaign_id") or payload.get("campaign_id")
        account_id = data.get("account_id") or data.get("tenant_id")
        contact_id = data.get("contact_id") or data.get("user_id") or data.get("id")

        if account_id is None and contact_id:
            context = await adapters.crm.build_contact_context(str(contact_id))
            if context and context.account:
                account_id = context.account.account_id

        funnel = await adapters.funnel.build_funnel_context(
            campaign_id=campaign_id,
            account_id=account_id,
        )
        spend = _coerce_float(data.get("spend"), default=0.0)
        avg_order_value = _coerce_float(data.get("avg_order_value"), default=75.0)
        roi = await adapters.analytics.estimate_roi(
            funnel,
            spend=spend,
            avg_order_value=avg_order_value,
        )

        logger.info(
            "campaign_event_processed",
            event_type=payload.get("event_type"),
            scope=scope,
            campaign_id=campaign_id,
            account_id=account_id,
            conversions=roi.get("conversions"),
            roi=roi.get("roi"),
        )

    return {
        "user-events": handle_user_event,
        "order-events": handle_order_event,
        "payment-events": handle_payment_event,
    }


def _coerce_float(value: object, *, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
