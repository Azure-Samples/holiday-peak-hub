"""Test configuration and fixtures for checkout support service."""
import pytest
from unittest.mock import AsyncMock

from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry


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
def sample_checkout_items():
    """Sample checkout items for testing."""
    return [
        {"sku": "SKU-001", "quantity": 2},
        {"sku": "SKU-002", "quantity": 1},
    ]


@pytest.fixture
def sample_checkout_request(sample_checkout_items):
    """Sample checkout request."""
    return {"items": sample_checkout_items}
