"""Test configuration and fixtures for product detail enrichment service."""
import pytest
from unittest.mock import AsyncMock

from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct


@pytest.fixture
def mock_catalog_product():
    """Create a mock catalog product."""
    return CatalogProduct(
        sku="SKU-001",
        name="Test Product",
        description="Base product description",
        price=99.99,
        category="electronics",
        brand="TestBrand",
        image_url="https://example.com/images/test.png",
    )


@pytest.fixture
def mock_inventory_context():
    """Create a mock inventory context."""
    return InventoryContext(
        sku="SKU-001",
        item=InventoryItem(
            sku="SKU-001",
            available=50,
            reserved=5,
            warehouse_id="WH-001",
        ),
        warehouses=[],
    )


@pytest.fixture
def mock_acp_content():
    """Create mock ACP content."""
    return {
        "sku": "SKU-001",
        "long_description": "Rich, ACP-supplied product description.",
        "features": ["Feature A", "Feature B", "Feature C"],
        "media": [{"type": "image", "url": "https://example.com/images/SKU-001.png"}],
    }


@pytest.fixture
def mock_review_summary():
    """Create mock review summary."""
    return {
        "sku": "SKU-001",
        "rating": 4.6,
        "review_count": 128,
        "highlights": ["Great quality", "Fast shipping"],
    }


@pytest.fixture
def mock_related_products():
    """Create mock related products."""
    return [
        CatalogProduct(
            sku="SKU-002",
            name="Related Product 1",
            description="Related product description",
            price=49.99,
            category="electronics",
            brand="TestBrand",
        ),
        CatalogProduct(
            sku="SKU-003",
            name="Related Product 2",
            description="Another related product",
            price=79.99,
            category="electronics",
            brand="OtherBrand",
        ),
    ]


@pytest.fixture
def mock_product_adapter(mock_catalog_product, mock_related_products):
    """Create a mock product adapter."""
    adapter = AsyncMock()
    adapter.get_product = AsyncMock(return_value=mock_catalog_product)
    adapter.get_related = AsyncMock(return_value=mock_related_products)
    return adapter


@pytest.fixture
def mock_inventory_adapter(mock_inventory_context):
    """Create a mock inventory adapter."""
    adapter = AsyncMock()
    adapter.build_inventory_context = AsyncMock(return_value=mock_inventory_context)
    return adapter


@pytest.fixture
def sample_enrichment_request():
    """Sample enrichment request."""
    return {"sku": "SKU-001", "related_limit": 4}
