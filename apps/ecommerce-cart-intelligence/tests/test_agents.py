"""Unit tests for CartIntelligenceAgent."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ecommerce_cart_intelligence.adapters import CartAdapters, CartAnalyticsAdapter
from ecommerce_cart_intelligence.agents import CartIntelligenceAgent, _coerce_cart_items
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry
from holiday_peak_lib.schemas.product import CatalogProduct, ProductContext


@pytest.fixture
def mock_adapters(
    mock_product_adapter,
    mock_pricing_adapter,
    mock_inventory_adapter,
    mock_analytics_adapter,
):
    """Create mock adapters container."""
    return CartAdapters(
        products=mock_product_adapter,
        pricing=mock_pricing_adapter,
        inventory=mock_inventory_adapter,
        analytics=mock_analytics_adapter,
    )


@pytest.fixture
def agent_config():
    """Create agent dependencies for testing."""
    return AgentDependencies(
        service_name="test-cart-intelligence",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


class TestCoerceCartItems:
    """Tests for cart items coercion."""

    def test_coerce_empty_items(self):
        """Test coercing empty items returns empty list."""
        assert _coerce_cart_items(None) == []
        assert _coerce_cart_items([]) == []

    def test_coerce_valid_items(self):
        """Test coercing valid cart items."""
        raw_items = [
            {"sku": "SKU-001", "quantity": 2},
            {"sku": "SKU-002", "quantity": 1},
        ]
        result = _coerce_cart_items(raw_items)
        assert len(result) == 2
        assert result[0]["sku"] == "SKU-001"
        assert result[0]["quantity"] == 2

    def test_coerce_items_with_missing_quantity(self):
        """Test coercing items with missing quantity defaults to 1."""
        raw_items = [{"sku": "SKU-001"}]
        result = _coerce_cart_items(raw_items)
        assert result[0]["quantity"] == 1

    def test_coerce_items_skips_invalid(self):
        """Test coercing skips items without sku."""
        raw_items = [
            {"sku": "SKU-001"},
            {"quantity": 2},  # Missing sku
            "invalid",  # Not a dict
        ]
        result = _coerce_cart_items(raw_items)
        assert len(result) == 1


class TestCartIntelligenceAgent:
    """Tests for CartIntelligenceAgent."""

    @pytest.mark.asyncio
    async def test_handle_empty_cart(self, agent_config):
        """Test handling an empty cart."""
        with patch("ecommerce_cart_intelligence.agents.build_cart_adapters") as mock_build:
            mock_analytics = AsyncMock()
            mock_analytics.estimate_abandonment_risk = AsyncMock(
                return_value={"risk_score": 0.1, "drivers": []}
            )
            mock_build.return_value = CartAdapters(
                products=AsyncMock(),
                pricing=AsyncMock(),
                inventory=AsyncMock(),
                analytics=mock_analytics,
            )
            agent = CartIntelligenceAgent(config=agent_config)
            result = await agent.handle({"items": []})

            assert result["service"] == "test-cart-intelligence"
            assert result["items"] == []
            assert "abandonment_risk" in result

    @pytest.mark.asyncio
    async def test_handle_with_items(self, agent_config, sample_cart_items):
        """Test handling cart with items."""
        mock_product_ctx = ProductContext(
            sku="SKU-001",
            product=CatalogProduct(
                sku="SKU-001",
                name="Test",
                description="Desc",
                amount=99.99,
                category="test",
                brand="TestBrand",
            ),
            related=[],
        )
        mock_pricing_ctx = PriceContext(
            sku="SKU-001",
            active=PriceEntry(sku="SKU-001", amount=99.99, currency="USD", promotional=True),
            offers=[],
        )
        mock_inventory_ctx = InventoryContext(
            sku="SKU-001",
            item=InventoryItem(sku="SKU-001", available=10, reserved=0, warehouse_id="WH1"),
            warehouses=[],
        )

        with patch("ecommerce_cart_intelligence.agents.build_cart_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.build_product_context = AsyncMock(return_value=mock_product_ctx)

            mock_pricing = AsyncMock()
            mock_pricing.build_price_context = AsyncMock(return_value=mock_pricing_ctx)

            mock_inventory = AsyncMock()
            mock_inventory.build_inventory_context = AsyncMock(return_value=mock_inventory_ctx)

            mock_analytics = AsyncMock()
            mock_analytics.estimate_abandonment_risk = AsyncMock(
                return_value={"risk_score": 0.2, "drivers": []}
            )

            mock_build.return_value = CartAdapters(
                products=mock_products,
                pricing=mock_pricing,
                inventory=mock_inventory,
                analytics=mock_analytics,
            )

            agent = CartIntelligenceAgent(config=agent_config)
            result = await agent.handle({"items": sample_cart_items, "user_id": "user-1"})

            assert result["service"] == "test-cart-intelligence"
            assert len(result["items"]) == 2
            assert "abandonment_risk" in result
            assert "product_contexts" in result
            assert "pricing_contexts" in result
            assert "inventory_contexts" in result
            assert "acp" in result
            assert result["acp"]["domain"] == "cart"


class TestCartAnalyticsAdapter:
    """Tests for CartAnalyticsAdapter."""

    @pytest.mark.asyncio
    async def test_low_risk_cart(self):
        """Test cart with low abandonment risk."""
        adapter = CartAnalyticsAdapter()
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
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=True),
                offers=[],
            )
        ]

        result = await adapter.estimate_abandonment_risk(
            items, inventory=inventory, pricing=pricing
        )

        assert result["risk_score"] <= 0.2
        assert len(result["drivers"]) == 0

    @pytest.mark.asyncio
    async def test_high_risk_out_of_stock(self):
        """Test cart with out-of-stock item has high risk."""
        adapter = CartAnalyticsAdapter()
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
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=True),
                offers=[],
            )
        ]

        result = await adapter.estimate_abandonment_risk(
            items, inventory=inventory, pricing=pricing
        )

        assert result["risk_score"] >= 0.4
        assert any("out of stock" in d for d in result["drivers"])

    @pytest.mark.asyncio
    async def test_medium_risk_low_stock(self):
        """Test cart with low stock has medium risk."""
        adapter = CartAnalyticsAdapter()
        items = [{"sku": "SKU-001", "quantity": 5}]
        inventory = [
            InventoryContext(
                sku="SKU-001",
                item=InventoryItem(sku="SKU-001", available=2, reserved=0, warehouse_id="WH1"),
                warehouses=[],
            )
        ]
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=True),
                offers=[],
            )
        ]

        result = await adapter.estimate_abandonment_risk(
            items, inventory=inventory, pricing=pricing
        )

        assert result["risk_score"] >= 0.2
        assert any("low stock" in d for d in result["drivers"])

    @pytest.mark.asyncio
    async def test_risk_missing_inventory(self):
        """Test cart with missing inventory data."""
        adapter = CartAnalyticsAdapter()
        items = [{"sku": "SKU-001", "quantity": 1}]
        inventory = [None]  # Missing inventory
        pricing = [
            PriceContext(
                sku="SKU-001",
                active=PriceEntry(sku="SKU-001", amount=10.0, currency="USD", promotional=True),
                offers=[],
            )
        ]

        result = await adapter.estimate_abandonment_risk(
            items, inventory=inventory, pricing=pricing
        )

        assert result["risk_score"] >= 0.2
        assert any("missing inventory" in d for d in result["drivers"])

    @pytest.mark.asyncio
    async def test_risk_no_promotion(self):
        """Test cart with no promotion has slight risk increase."""
        adapter = CartAnalyticsAdapter()
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

        result = await adapter.estimate_abandonment_risk(
            items, inventory=inventory, pricing=pricing
        )

        assert any("no promotion" in d for d in result["drivers"])
