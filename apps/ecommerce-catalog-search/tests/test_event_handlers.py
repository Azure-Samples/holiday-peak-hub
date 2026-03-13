"""Unit tests for catalog search event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ecommerce_catalog_search.event_handlers import build_event_handlers
from holiday_peak_lib.schemas.inventory import InventoryItem


def test_build_event_handlers_includes_product_events() -> None:
    handlers = build_event_handlers()
    assert "product-events" in handlers
    assert callable(handlers["product-events"])


class _FakeEvent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def body_as_str(self) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_product_delete_event_deletes_index_document() -> None:
    adapters = Mock()
    adapters.products = AsyncMock()
    adapters.inventory = AsyncMock()
    adapters.mapping = Mock()

    with (
        patch("ecommerce_catalog_search.event_handlers.build_catalog_adapters", return_value=adapters),
        patch(
            "ecommerce_catalog_search.event_handlers.delete_catalog_document",
            new=AsyncMock(return_value=True),
        ) as mock_delete,
    ):
        handlers = build_event_handlers()
        event = _FakeEvent(
            {
                "event_type": "ProductDeleted",
                "data": {"sku": "SKU-001"},
            }
        )

        await handlers["product-events"](None, event)

        mock_delete.assert_awaited_once_with("SKU-001")
        adapters.products.get_product.assert_not_awaited()


@pytest.mark.asyncio
async def test_product_update_event_upserts_index_document(mock_catalog_product) -> None:
    inventory_item = InventoryItem(
        sku="SKU-001", available=4, reserved=0, warehouse_id="WH1"
    )

    adapters = Mock()
    adapters.products = AsyncMock()
    adapters.products.get_product = AsyncMock(return_value=mock_catalog_product)
    adapters.inventory = AsyncMock()
    adapters.inventory.get_item = AsyncMock(return_value=inventory_item)
    adapters.mapping = Mock()
    adapters.mapping.to_acp_product = Mock(return_value={"item_id": "SKU-001"})

    with (
        patch("ecommerce_catalog_search.event_handlers.build_catalog_adapters", return_value=adapters),
        patch(
            "ecommerce_catalog_search.event_handlers.upsert_catalog_document",
            new=AsyncMock(return_value=True),
        ) as mock_upsert,
    ):
        handlers = build_event_handlers()
        event = _FakeEvent(
            {
                "event_type": "ProductUpdated",
                "data": {"sku": "SKU-001"},
            }
        )

        await handlers["product-events"](None, event)

        mock_upsert.assert_awaited_once()
        uploaded_document = mock_upsert.await_args.args[0]
        assert uploaded_document["id"] == "SKU-001"
        assert uploaded_document["sku"] == "SKU-001"
