"""Adapters for the ecommerce order status service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector
from holiday_peak_lib.adapters.mock_adapters import MockLogisticsAdapter


@dataclass
class OrderStatusAdapters:
    """Container for order status adapters."""

    logistics: LogisticsConnector
    resolver: "OrderTrackingResolver"


class OrderTrackingResolver:
    """Resolve tracking identifiers for orders (stub)."""

    async def resolve_tracking_id(self, order_id: str) -> str:
        return f"T-{order_id}"


def build_order_status_adapters(
    *,
    logistics_connector: Optional[LogisticsConnector] = None,
) -> OrderStatusAdapters:
    """Create adapters for order status workflows."""
    logistics = logistics_connector or LogisticsConnector(adapter=MockLogisticsAdapter())
    resolver = OrderTrackingResolver()
    return OrderStatusAdapters(logistics=logistics, resolver=resolver)
