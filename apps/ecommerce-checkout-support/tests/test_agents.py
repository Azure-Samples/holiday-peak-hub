"""Unit tests for CheckoutSupportAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from ecommerce_checkout_support.adapters import (
    CheckoutAdapters,
    CheckoutValidationAdapter,
)
from ecommerce_checkout_support.agents import CheckoutSupportAgent, _coerce_items
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry


@pytest.fixture
def agent_config():
    """Create agent dependencies for testing."""
    return AgentDependencies(
        service_name="test-checkout-support",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


class TestCoerceItems:
    """Tests for item coercion."""

    def test_coerce_empty_items(self):
        """Test coercing empty items returns empty list."""
        assert _coerce_items(None) == []
        assert _coerce_items([]) == []

    def test_coerce_valid_items(self):
        """Test coercing valid checkout items."""
        raw_items = [
            {"sku": "SKU-001", "quantity": 2},
            {"sku": "SKU-002", "quantity": 1},
        ]
        result = _coerce_items(raw_items)
        assert len(result) == 2
        assert result[0]["sku"] == "SKU-001"
        assert result[0]["quantity"] == 2


class TestCheckoutValidationAdapter:
    """Tests for CheckoutValidationAdapter."""

    @pytest.mark.asyncio
    async def test_validate_ready_cart(self):
        """Test validation of a ready-to-checkout cart."""
        adapter = CheckoutValidationAdapter()
        items = [{"sku": "SKU-001", "quantity": 1}]
        inventory = [
            InventoryContext(
                sku="SKU-001",
                item=InventoryItem(sku="SKU-001", available=100, reserved=0, warehouse_id="WH1"),
                warehouses=[],
            )
        ]
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=False),
                offers=[],
            )
        ]

        result = await adapter.validate(items, pricing=pricing, inventory=inventory)

        assert result["status"] == "ready"
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_out_of_stock(self):
        """Test validation detects out of stock items."""
        adapter = CheckoutValidationAdapter()
        items = [{"sku": "SKU-001", "quantity": 1}]
        inventory = [
            InventoryContext(
                sku="SKU-001",
                item=InventoryItem(sku="SKU-001", available=0, reserved=0, warehouse_id="WH1"),
                warehouses=[],
            )
        ]
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=False),
                offers=[],
            )
        ]

        result = await adapter.validate(items, pricing=pricing, inventory=inventory)

        assert result["status"] == "blocked"
        assert any(i["type"] == "out_of_stock" for i in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_insufficient_stock(self):
        """Test validation detects insufficient stock."""
        adapter = CheckoutValidationAdapter()
        items = [{"sku": "SKU-001", "quantity": 10}]
        inventory = [
            InventoryContext(
                sku="SKU-001",
                item=InventoryItem(sku="SKU-001", available=5, reserved=0, warehouse_id="WH1"),
                warehouses=[],
            )
        ]
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=False),
                offers=[],
            )
        ]

        result = await adapter.validate(items, pricing=pricing, inventory=inventory)

        assert result["status"] == "blocked"
        assert any(i["type"] == "insufficient_stock" for i in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_missing_inventory(self):
        """Test validation detects missing inventory."""
        adapter = CheckoutValidationAdapter()
        items = [{"sku": "SKU-001", "quantity": 1}]
        inventory = [None]
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=False),
                offers=[],
            )
        ]

        result = await adapter.validate(items, pricing=pricing, inventory=inventory)

        assert result["status"] == "blocked"
        assert any(i["type"] == "inventory_missing" for i in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_missing_price(self):
        """Test validation detects missing price."""
        adapter = CheckoutValidationAdapter()
        items = [{"sku": "SKU-001", "quantity": 1}]
        inventory = [
            InventoryContext(
                sku="SKU-001",
                item=InventoryItem(sku="SKU-001", available=100, reserved=0, warehouse_id="WH1"),
                warehouses=[],
            )
        ]
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=None,  # Missing price
                offers=[],
            )
        ]

        result = await adapter.validate(items, pricing=pricing, inventory=inventory)

        assert result["status"] == "blocked"
        assert any(i["type"] == "missing_price" for i in result["issues"])


class TestCheckoutSupportAgent:
    """Tests for CheckoutSupportAgent."""

    @pytest.mark.asyncio
    async def test_handle_valid_checkout(self, agent_config):
        """Test handling a valid checkout."""
        mock_pricing_ctx = PriceContext(
            sku="SKU-001",
            active=PriceEntry(sku="SKU-001", amount=50.0, currency="USD", promotional=True),
            offers=[],
        )
        mock_inventory_ctx = InventoryContext(
            sku="SKU-001",
            item=InventoryItem(sku="SKU-001", available=100, reserved=0, warehouse_id="WH1"),
            warehouses=[],
        )

        with patch("ecommerce_checkout_support.agents.build_checkout_adapters") as mock_build:
            mock_pricing = AsyncMock()
            mock_pricing.build_price_context = AsyncMock(return_value=mock_pricing_ctx)

            mock_inventory = AsyncMock()
            mock_inventory.build_inventory_context = AsyncMock(return_value=mock_inventory_ctx)

            mock_validator = AsyncMock()
            mock_validator.validate = AsyncMock(return_value={"status": "ready", "issues": []})

            mock_build.return_value = CheckoutAdapters(
                pricing=mock_pricing,
                inventory=mock_inventory,
                validator=mock_validator,
            )

            agent = CheckoutSupportAgent(config=agent_config)
            result = await agent.handle({"items": [{"sku": "SKU-001", "quantity": 1}]})

            assert result["service"] == "test-checkout-support"
            assert "validation" in result
            assert result["validation"]["status"] == "ready"
            assert "acp" in result
            assert result["acp"]["domain"] == "checkout"

    @pytest.mark.asyncio
    async def test_handle_empty_checkout(self, agent_config):
        """Test handling empty checkout."""
        with patch("ecommerce_checkout_support.agents.build_checkout_adapters") as mock_build:
            mock_validator = AsyncMock()
            mock_validator.validate = AsyncMock(return_value={"status": "ready", "issues": []})

            mock_build.return_value = CheckoutAdapters(
                pricing=AsyncMock(),
                inventory=AsyncMock(),
                validator=mock_validator,
            )

            agent = CheckoutSupportAgent(config=agent_config)
            result = await agent.handle({"items": []})

            assert result["service"] == "test-checkout-support"
            assert result["items"] == []
