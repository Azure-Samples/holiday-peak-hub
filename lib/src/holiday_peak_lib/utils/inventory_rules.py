"""Shared inventory stock classification rules.

Centralizes the business logic for evaluating item-level stock status so
that cart-intelligence, checkout-support, and inventory-health adapters
share a single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from holiday_peak_lib.schemas.inventory import InventoryContext


class StockStatus(str, Enum):
    """Canonical stock classification for a single SKU."""

    AVAILABLE = "available"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class StockClassification:
    """Result of classifying an item's stock status."""

    sku: str
    status: StockStatus
    available: int
    requested: int


def classify_item_stock(
    sku: str,
    quantity: int,
    inventory: InventoryContext | None,
) -> StockClassification:
    """Classify item stock level from inventory context.

    Returns a :class:`StockClassification` that adapters can map to their
    domain-specific responses (risk scores, blocking issues, health flags).
    """
    if inventory is None:
        return StockClassification(
            sku=sku, status=StockStatus.MISSING, available=0, requested=quantity
        )
    available = inventory.item.available
    if available <= 0:
        return StockClassification(
            sku=sku, status=StockStatus.OUT_OF_STOCK, available=available, requested=quantity
        )
    if available < quantity:
        return StockClassification(
            sku=sku, status=StockStatus.LOW_STOCK, available=available, requested=quantity
        )
    return StockClassification(
        sku=sku, status=StockStatus.AVAILABLE, available=available, requested=quantity
    )
