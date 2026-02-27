"""Test configuration and fixtures for catalog search service."""

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct


@pytest.fixture
def mock_catalog_product():
    """Create a mock catalog product."""
    return CatalogProduct(
        sku="SKU-001",
        name="Test Product",
        description="A test product for searching",
        price=99.99,
        category="electronics",
        brand="TestBrand",
        image_url="https://example.com/images/test.png",
    )


@pytest.fixture
def mock_catalog_products(mock_catalog_product):
    """Create a list of mock catalog products."""
    return [
        mock_catalog_product,
        CatalogProduct(
            sku="SKU-002",
            name="Another Product",
            description="Another test product",
            price=49.99,
            category="electronics",
            brand="TestBrand",
        ),
    ]


@pytest.fixture
def mock_inventory_item():
    """Create a mock inventory item."""
    return InventoryItem(
        sku="SKU-001",
        available=50,
        reserved=5,
        warehouse_id="WH-001",
    )


@pytest.fixture
def mock_inventory_context(mock_inventory_item):
    """Create a mock inventory context."""
    return InventoryContext(
        sku="SKU-001",
        item=mock_inventory_item,
        warehouses=[],
    )


@pytest.fixture
def mock_product_adapter(mock_catalog_product, mock_catalog_products):
    """Create a mock product adapter."""
    adapter = AsyncMock()
    adapter.get_product = AsyncMock(return_value=mock_catalog_product)
    adapter.get_related = AsyncMock(return_value=mock_catalog_products[1:])
    adapter.search = AsyncMock(return_value=mock_catalog_products)
    return adapter


@pytest.fixture
def mock_inventory_adapter(mock_inventory_item, mock_inventory_context):
    """Create a mock inventory adapter."""
    adapter = AsyncMock()
    adapter.get_item = AsyncMock(return_value=mock_inventory_item)
    adapter.build_inventory_context = AsyncMock(return_value=mock_inventory_context)
    return adapter


@pytest.fixture
def sample_search_request():
    """Sample search request."""
    return {"query": "test product", "limit": 5}
