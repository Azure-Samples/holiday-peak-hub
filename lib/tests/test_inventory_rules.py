"""Tests for shared inventory stock classification rules."""

from __future__ import annotations

import pytest
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.utils.inventory_rules import (
    StockClassification,
    StockStatus,
    classify_item_stock,
)


def _make_context(available: int, reserved: int = 0) -> InventoryContext:
    """Create a minimal InventoryContext for testing."""
    return InventoryContext(
        item=InventoryItem(sku="SKU-1", available=available, reserved=reserved),
        warehouses=[],
    )


class TestClassifyItemStock:
    def test_missing_inventory_returns_missing(self) -> None:
        result = classify_item_stock("SKU-1", quantity=1, inventory=None)
        assert result == StockClassification(
            sku="SKU-1", status=StockStatus.MISSING, available=0, requested=1
        )

    def test_zero_available_returns_out_of_stock(self) -> None:
        result = classify_item_stock("SKU-1", quantity=1, inventory=_make_context(0))
        assert result.status == StockStatus.OUT_OF_STOCK
        assert result.available == 0

    def test_negative_available_returns_out_of_stock(self) -> None:
        result = classify_item_stock("SKU-1", quantity=1, inventory=_make_context(-3))
        assert result.status == StockStatus.OUT_OF_STOCK

    def test_available_less_than_quantity_returns_low_stock(self) -> None:
        result = classify_item_stock("SKU-1", quantity=5, inventory=_make_context(3))
        assert result.status == StockStatus.LOW_STOCK
        assert result.available == 3
        assert result.requested == 5

    def test_available_equals_quantity_returns_available(self) -> None:
        result = classify_item_stock("SKU-1", quantity=5, inventory=_make_context(5))
        assert result.status == StockStatus.AVAILABLE

    def test_available_exceeds_quantity_returns_available(self) -> None:
        result = classify_item_stock("SKU-1", quantity=2, inventory=_make_context(100))
        assert result.status == StockStatus.AVAILABLE
        assert result.available == 100

    def test_classification_is_frozen(self) -> None:
        result = classify_item_stock("SKU-1", quantity=1, inventory=_make_context(10))
        with pytest.raises(AttributeError):
            result.status = StockStatus.MISSING  # type: ignore[misc]
