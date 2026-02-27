"""Test configuration and fixtures for cart intelligence service."""
import pytest
from unittest.mock import AsyncMock

from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry
from holiday_peak_lib.schemas.product import ProductContext, CatalogProduct


@pytest.fixture
def mock_product_context():
    """Create a mock product context."""
    return ProductContext(
        sku="SKU-001",
        product=CatalogProduct(
            sku="SKU-001",
            name="Test Product",
            description="Test Description",
            price=99.99,
            category="electronics",
            brand="TestBrand",
        ),
        related=[
            CatalogProduct(
                sku="SKU-002",
                name="Related Product",
                description="Related Description",
                price=49.99,
                category="electronics",
                brand="TestBrand",
            )
        ],
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
def mock_pricing_context():
    """Create a mock pricing context."""
    return PriceContext(
        sku="SKU-001",
        active=PriceEntry(
            sku="SKU-001",
            amount=99.99,
            currency="USD",
            promotional=True,
        ),
        offers=[],
    )


@pytest.fixture
def mock_product_adapter(mock_product_context):
    """Create a mock product adapter."""
    adapter = AsyncMock()
    adapter.build_product_context = AsyncMock(return_value=mock_product_context)
    adapter.get_product = AsyncMock(return_value=mock_product_context.product)
    adapter.get_related = AsyncMock(return_value=mock_product_context.related)
    return adapter


@pytest.fixture
def mock_pricing_adapter(mock_pricing_context):
    """Create a mock pricing adapter."""
    adapter = AsyncMock()
    adapter.build_price_context = AsyncMock(return_value=mock_pricing_context)
    return adapter


@pytest.fixture
def mock_inventory_adapter(mock_inventory_context):
    """Create a mock inventory adapter."""
    adapter = AsyncMock()
    adapter.build_inventory_context = AsyncMock(return_value=mock_inventory_context)
    return adapter


@pytest.fixture
def mock_analytics_adapter():
    """Create a mock analytics adapter."""
    adapter = AsyncMock()
    adapter.estimate_abandonment_risk = AsyncMock(
        return_value={"risk_score": 0.25, "drivers": []}
    )
    return adapter


@pytest.fixture
def sample_cart_items():
    """Sample cart items for testing."""
    return [
        {"sku": "SKU-001", "quantity": 2},
        {"sku": "SKU-002", "quantity": 1},
    ]


@pytest.fixture
def sample_cart_request(sample_cart_items):
    """Sample cart intelligence request."""
    return {
        "items": sample_cart_items,
        "user_id": "user-123",
        "related_limit": 3,
        "price_limit": 5,
    }
