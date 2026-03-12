"""Backward-compatible product-events handlers for consistency validation."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.utils.event_hub import EventHandler


def build_event_handlers() -> dict[str, EventHandler]:
    """Return handlers keyed by Event Hub topic name.

    This compatibility shim keeps the legacy ``product-events`` subscription
    wired while completeness logic has moved to ``completeness-jobs``.
    """

    async def handle_product_event(partition_context: Any, event: Any) -> None:
        _ = partition_context, event

    return {"product-events": handle_product_event}
