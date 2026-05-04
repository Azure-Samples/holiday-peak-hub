"""Unit tests for CatalogSearchAgent."""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest
from ecommerce_catalog_search.adapters import AcpCatalogMapper, CatalogAdapters
from ecommerce_catalog_search.agents import (
    CatalogSearchAgent,
    _deterministic_intent_policy,
    _parse_intent_response,
)
from ecommerce_catalog_search.ai_search import AISearchDocumentResult, AISearchSkuResult
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.schemas.inventory import InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct
from holiday_peak_lib.schemas.truth import IntentClassification


@pytest.fixture(name="agent_dependencies")
def fixture_agent_dependencies():
    """Create agent dependencies for testing."""
    return AgentDependencies(
        service_name="test-catalog-search",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


class TestAcpCatalogMapper:
    """Tests for AcpCatalogMapper."""

    def test_to_acp_product_full_product(self, mock_catalog_product):
        """Test mapping a full product to ACP format."""
        mapper = AcpCatalogMapper()
        result = mapper.to_acp_product(mock_catalog_product, availability="in_stock")

        assert result["item_id"] == "SKU-001"
        assert result["title"] == "Test Product"
        assert result["brand"] == "TestBrand"
        assert result["availability"] == "in_stock"
        assert result["price"] == "99.99 usd"
        assert result["is_eligible_search"] is True
        assert result["is_eligible_checkout"] is True
        assert "url" in result
        assert "image_url" in result

    def test_to_acp_product_minimal_product(self):
        """Test mapping a minimal product to ACP format."""
        mapper = AcpCatalogMapper()
        product = CatalogProduct(
            sku="MIN-001",
            name="Minimal Product",
            description=None,
            price=None,
            category="uncategorized",
            brand=None,
        )
        result = mapper.to_acp_product(product, availability="out_of_stock")

        assert result["item_id"] == "MIN-001"
        assert result["title"] == "Minimal Product"
        assert result["description"] == ""
        assert result["brand"] == ""
        assert result["price"] == "0.00 usd"
        assert result["availability"] == "out_of_stock"
        # Should use placeholder image
        assert "placeholder" in result["image_url"]

    def test_to_acp_product_custom_currency(self, mock_catalog_product):
        """Test mapping with custom currency."""
        mapper = AcpCatalogMapper()
        result = mapper.to_acp_product(
            mock_catalog_product, availability="in_stock", currency="eur"
        )

        assert result["price"] == "99.99 eur"


class TestCatalogSearchAgent:
    """Tests for CatalogSearchAgent."""

    @pytest.mark.asyncio
    async def test_handle_search_query(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Test handling a search query."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test product", "limit": 5})

            assert result["service"] == "test-catalog-search"
            assert result["query"] == "test product"
            assert "results" in result
            assert len(result["results"]) == 1
            # Verify ACP format
            assert result["results"][0]["item_id"] == "SKU-001"

    @pytest.mark.asyncio
    async def test_handle_response_includes_search_context_fields(
        self, agent_dependencies, mock_catalog_product
    ):
        """Response should expose requested_mode/search_stage/effective session id."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle(
                {
                    "query": "test product",
                    "limit": 5,
                    "mode": "unsupported-mode",
                    "session_id": "session-123",
                }
            )

            assert result["mode"] == "intelligent"
            assert result["requested_mode"] == "unsupported-mode"
            assert result["search_stage"] == "baseline"
            assert result["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_handle_defaults_requested_mode_to_intelligent_when_mode_missing(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Missing mode should default requested/effective mode to intelligent."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test product", "limit": 5})

            assert result["requested_mode"] == "intelligent"
            assert result["mode"] == "intelligent"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_handle_model_timeout_returns_hard_error_in_intelligent_mode(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Intelligent mode: model timeout in intent classification falls back
        to deterministic intent, but pipeline completes because the NL model
        answer step is skipped in strict mode."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            agent.slm = object()
            agent.invoke_model = AsyncMock(side_effect=asyncio.TimeoutError())

            result = await agent.handle(
                {
                    "query": "test product",
                    "limit": 5,
                }
            )

            # Intent classification falls back to deterministic, NL model
            # answer is skipped in strict mode, pipeline succeeds.
            assert result["result_type"] == "deterministic"
            assert result["degraded"] is False
            assert len(result["results"]) > 0

    @pytest.mark.asyncio
    async def test_handle_keyword_mode_returns_deterministic_without_model(
        self, agent_dependencies, mock_catalog_product
    ):
        """Keyword mode skips model answer and returns deterministic response."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            agent.slm = object()
            agent.invoke_model = AsyncMock(side_effect=asyncio.TimeoutError())

            result = await agent.handle(
                {
                    "query": "rain jacket",
                    "limit": 5,
                    "mode": "keyword",
                }
            )

            assert result["result_type"] == "deterministic"
            assert result["degraded"] is False
            assert result["model_attempted"] is False
            agent.invoke_model.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_model_error_returns_hard_error_in_intelligent_mode(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Intelligent mode: model error in intent falls back to deterministic
        intent, NL model answer is skipped, pipeline completes."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            agent.slm = object()
            agent.invoke_model = AsyncMock(side_effect=RuntimeError("model failure"))

            result = await agent.handle(
                {
                    "query": "test product",
                    "limit": 5,
                    "mode": "intelligent",
                }
            )

            # Intent classification falls back, NL model answer skipped
            assert result["result_type"] == "deterministic"
            assert result["degraded"] is False
            assert len(result["results"]) > 0

    @pytest.mark.asyncio
    async def test_handle_without_model_returns_non_degraded_deterministic_response(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Deterministic path should not be flagged as degraded when no model is configured."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle(
                {
                    "query": "running shoes",
                    "limit": 3,
                    "mode": "intelligent",
                }
            )

            assert result["answer_source"] == "agent_fallback"
            assert result["result_type"] == "deterministic"
            assert result["degraded"] is False
            assert result["model_attempted"] is False
            assert "degraded_reason" not in result
            assert "fallback_keywords" not in result

    @pytest.mark.asyncio
    async def test_handle_model_success_returns_model_answer_metadata(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Even when model could succeed, intelligent mode skips model answer
        for speed — result is deterministic, not model_answer."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            agent.slm = object()
            agent.invoke_model = AsyncMock(
                return_value={
                    "service": "test-catalog-search",
                    "results": [],
                    "mode": "intelligent",
                }
            )

            result = await agent.handle(
                {
                    "query": "rain jacket",
                    "limit": 5,
                    "mode": "intelligent",
                }
            )

            # Model answer skipped in strict mode — returns deterministic
            assert result["answer_source"] == "agent_fallback"
            assert result["result_type"] == "deterministic"
            assert result["degraded"] is False
            assert result["model_attempted"] is False

    @pytest.mark.asyncio
    async def test_handle_intelligent_mode_skips_model_answer(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Intelligent (strict) mode skips the NL model answer step and
        returns deterministic results directly for speed."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            agent.slm = object()
            agent.invoke_model = AsyncMock(
                return_value={
                    "service": "test-catalog-search",
                    "results": [],
                    "mode": "intelligent",
                }
            )

            result = await agent.handle(
                {
                    "query": "rain jacket",
                    "limit": 5,
                    "mode": "intelligent",
                }
            )

            # Intelligent mode skips model answer for speed
            assert result["answer_source"] == "agent_fallback"
            assert result["result_type"] == "deterministic"
            assert result["model_attempted"] is False

    @pytest.mark.asyncio
    async def test_handle_persists_search_history_to_memory_tiers(
        self, agent_dependencies, mock_catalog_product
    ):
        """Search requests should persist history across hot/warm/cold tiers."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            mock_hot_memory = AsyncMock()
            mock_hot_memory.get = AsyncMock(return_value=None)
            mock_hot_memory.set = AsyncMock()
            mock_warm_memory = AsyncMock()
            mock_warm_memory.upsert = AsyncMock()
            mock_cold_memory = AsyncMock()
            mock_cold_memory.upload_text = AsyncMock()

            agent.hot_memory = mock_hot_memory
            agent.warm_memory = mock_warm_memory
            agent.cold_memory = mock_cold_memory

            await agent.handle(
                {
                    "query": "SKU-001",
                    "limit": 5,
                    "mode": "keyword",
                    "search_stage": "rerank",
                    "session_id": "session-abc",
                    "query_history": ["old query"],
                }
            )

            assert mock_hot_memory.get.await_count == 1
            assert mock_hot_memory.set.await_count == 1
            assert mock_hot_memory.set.await_args.kwargs["key"] == (
                "v1|svc=test-catalog-search|ten=public|ses=session-abc"
                "|key=catalog-search-history"
            )
            assert mock_warm_memory.upsert.await_count == 1
            warm_record = mock_warm_memory.upsert.await_args.args[0]
            assert warm_record["session_id"] == "session-abc"
            assert warm_record["search_stage"] == "rerank"
            assert warm_record["result_skus"] == ["SKU-001"]
            assert mock_cold_memory.upload_text.await_count == 1

    @pytest.mark.asyncio
    async def test_handle_falls_back_session_id_to_user_ip(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Effective session_id should fallback to user_ip when session/user are absent."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test", "limit": 5, "user_ip": "203.0.113.9"})

            assert result["session_id"] == "203.0.113.9"

    @pytest.mark.asyncio
    async def test_handle_empty_query(self, agent_dependencies):
        """Test handling an empty search query."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_kw_search.return_value = []

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=None)
            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "", "limit": 5})

            assert result["service"] == "test-catalog-search"
            assert result["query"] == ""
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_handle_respects_limit(
        self, agent_dependencies, mock_catalog_products, mock_keyword_search_result
    ):
        """Test that search respects limit parameter."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_products[0])
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test", "limit": 1})

            assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_handle_uses_ai_search_results(self, agent_dependencies, mock_catalog_product):
        """Test configured AI Search path uses returned SKU order."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test product", "limit": 5, "mode": "keyword"})

            assert len(result["results"]) == 1
            assert result["results"][0]["item_id"] == "SKU-001"
            mock_search.assert_awaited_once_with(query="test product", limit=5)
            mock_products.get_related.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_falls_back_when_ai_search_empty(
        self, agent_dependencies, mock_catalog_product
    ):
        """Natural-language keyword queries should return empty when retrieval has no relevant hits."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=[])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "fallback query", "limit": 3, "mode": "keyword"})

            assert len(result["results"]) == 0
            mock_search.assert_awaited_once_with(query="fallback query", limit=3)
            mock_products.get_related.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_uses_text_search_fallback_when_ai_search_empty(
        self, agent_dependencies, mock_catalog_product
    ):
        """Keyword search should use deterministic text fallback before hash-SKU fallback."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=[])

            mock_products = AsyncMock()
            text_match_product = mock_catalog_product.model_copy(
                update={
                    "name": "Rain Jacket",
                    "description": "Waterproof rain jacket for cold weather travel.",
                    "category": "clothing",
                }
            )
            mock_products.search = AsyncMock(return_value=[text_match_product])
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "rain jacket", "limit": 3, "mode": "keyword"})

            assert len(result["results"]) == 1
            assert result["results"][0]["item_id"] == "SKU-001"
            mock_products.search.assert_awaited_once_with(query="rain jacket", limit=3)
            mock_products.get_product.assert_not_awaited()
            mock_products.get_related.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_preserves_sku_like_fallback_behavior(
        self, agent_dependencies, mock_catalog_product
    ):
        """SKU-like queries should keep hash-SKU fallback behavior and skip text search."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=[])

            mock_products = AsyncMock()
            mock_products.search = AsyncMock(return_value=[mock_catalog_product])
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "SKU-001", "limit": 3, "mode": "keyword"})

            assert len(result["results"]) == 1
            assert result["results"][0]["item_id"] == "SKU-001"
            mock_products.search.assert_not_awaited()
            mock_products.get_related.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_logs_fallback_reason_when_ai_search_degraded(
        self, agent_dependencies, mock_catalog_product, caplog
    ):
        """Test fallback reason from AI Search degradation is logged by caller path."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
        ):
            mock_search.return_value = AISearchSkuResult(
                skus=[],
                fallback_reason="ai_search_transport_error",
            )
            mock_multi.return_value = []

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            caplog.set_level(logging.WARNING, logger="ecommerce_catalog_search.agents")

            agent = CatalogSearchAgent(config=agent_dependencies)
            await agent.handle({"query": "fallback query", "limit": 3, "mode": "keyword"})

            assert any(
                record.msg == "catalog_search_fallback_path"
                and getattr(record, "fallback_reason", None) == "ai_search_transport_error"
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_handle_strict_mode_blocks_non_ai_fallback_when_ai_search_degraded(
        self,
        agent_dependencies,
        mock_catalog_product,
        monkeypatch,
    ):
        """Strict mode should not silently fallback when AI Search dependency is degraded."""
        monkeypatch.setenv("CATALOG_SEARCH_REQUIRE_AI_SEARCH", "true")

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(
                skus=[],
                fallback_reason="ai_search_transport_error",
            )
            mock_kw_search.return_value = []

            mock_products = AsyncMock()
            mock_products.search = AsyncMock(return_value=[mock_catalog_product])
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[mock_catalog_product])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=None)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "fallback query", "limit": 3})

            assert result["results"] == []
            mock_products.search.assert_not_awaited()
            mock_products.get_product.assert_not_awaited()
            mock_products.get_related.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_intelligent_mode_falls_back_on_low_confidence(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Intelligent mode runs both search paths even with low-confidence intent."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])
            mock_multi.return_value = []
            mock_kw_search.return_value = mock_keyword_search_result

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with (
                patch.object(agent, "_assess_complexity", return_value=1.0),
                patch.object(
                    agent,
                    "classify_intent",
                    new=AsyncMock(
                        return_value=IntentClassification(
                            intent="semantic_search",
                            confidence=0.45,
                            entities={"category": "electronics"},
                        )
                    ),
                ),
            ):
                result = await agent.handle(
                    {"query": "show me travel accessories", "limit": 5, "mode": "intelligent"}
                )

            # Low confidence still runs both keyword and hybrid in parallel
            assert len(result["results"]) == 1
            mock_multi.assert_awaited_once()
            assert mock_kw_search.await_count >= 1

    @pytest.mark.asyncio
    async def test_handle_intelligent_mode_runs_multi_query_and_merges_enrichment(
        self, agent_dependencies, mock_catalog_product, mock_keyword_search_result
    ):
        """Intelligent mode should use multi-query retrieval and surface enriched fields."""
        mock_inventory_item = InventoryItem(sku="SKU-001", available=10, reserved=0)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=[])
            mock_kw_search.return_value = mock_keyword_search_result
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-001",
                    score=0.98,
                    document={"sku": "SKU-001"},
                    enriched_fields={
                        "use_cases": ["travel", "commute"],
                        "complementary_products": ["SKU-321"],
                        "substitute_products": ["SKU-654"],
                        "enriched_description": "Noise-canceling headphones for travel.",
                    },
                )
            ]

            mock_products = AsyncMock()
            relevant_product = mock_catalog_product.model_copy(
                update={
                    "name": "Travel Headphones Pro",
                    "description": "Noise-canceling headphones for travel and commute.",
                    "category": "audio",
                }
            )
            mock_products.get_product = AsyncMock(return_value=relevant_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=mock_inventory_item)

            mock_mapping = AcpCatalogMapper()

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=mock_mapping,
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with (
                patch.object(agent, "_assess_complexity", return_value=0.95),
                patch.object(
                    agent,
                    "classify_intent",
                    new=AsyncMock(
                        return_value=IntentClassification(
                            intent="semantic_search",
                            confidence=0.91,
                            entities={"category": "audio", "keywords": ["travel"]},
                        )
                    ),
                ),
            ):
                result = await agent.handle(
                    {"query": "best headphones for travel", "limit": 5, "mode": "intelligent"}
                )

            first = result["results"][0]
            assert first["item_id"] == "SKU-001"
            assert first["use_cases"] == ["travel", "commute"]
            assert first["complementary_products"] == ["SKU-321"]
            assert first["substitute_products"] == ["SKU-654"]
            assert "extended_attributes" in first
            assert first["extended_attributes"]["enriched_description"].startswith(
                "Noise-canceling"
            )
            mock_multi.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_classify_intent_uses_generic_semantic_fallback_for_complex_query(
        self, agent_dependencies
    ):
        """Complex queries should map to generic semantic intent fallback."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        intent = await agent.classify_intent(
            "compare wireless noise cancelling headphones under 200"
        )

        assert intent.intent == "semantic_search"
        assert intent.query_type == "complex"
        assert intent.use_case == "product discovery"
        assert "headphone" in intent.entities["keywords"]

    @pytest.mark.asyncio
    async def test_classify_intent_uses_generic_keyword_fallback_for_simple_query(
        self, agent_dependencies
    ):
        """Simple queries should remain generic keyword lookup."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        intent = await agent.classify_intent("running shoes")

        assert intent.intent == "keyword_lookup"
        assert intent.query_type == "simple"
        assert any(keyword in intent.entities["keywords"] for keyword in ("shoe", "shoes"))

    @pytest.mark.asyncio
    async def test_classify_intent_merges_model_keywords_with_generic_fallback(
        self, agent_dependencies
    ):
        """Low-signal model output should be merged with generic fallback keywords."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        agent.slm = object()
        agent.invoke_model = AsyncMock(
            return_value={
                "intent": "keyword_lookup",
                "confidence": 0.4,
                "entities": {"keywords": []},
            }
        )

        intent = await agent.classify_intent("wireless headphones battery life")

        assert intent.intent == "keyword_lookup"
        assert any(
            keyword in intent.entities["keywords"]
            for keyword in ("wireless", "headphone", "battery")
        )
        agent.invoke_model.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_classify_intent_prefers_high_confidence_model_intent(self, agent_dependencies):
        """Model-provided generic semantic intent should be honored when high confidence."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        agent.slm = object()
        agent.invoke_model = AsyncMock(
            return_value={
                "intent": "semantic_search",
                "confidence": 0.91,
                "queryType": "complex",
                "useCase": "product discovery",
                "entities": {
                    "keywords": ["gaming", "laptop"],
                    "subQueries": ["gaming laptop", "rtx laptop"],
                },
            }
        )

        intent = await agent.classify_intent("best gaming laptop under 1500")

        assert intent.intent == "semantic_search"
        assert intent.confidence >= 0.9
        assert intent.query_type == "complex"
        assert "gaming" in intent.entities["keywords"]

    @pytest.mark.asyncio
    async def test_handle_keyword_mode_executes_single_keyword_cycle(self, agent_dependencies):
        """Keyword mode should run one generic keyword retrieval cycle."""
        keyword_products = [
            CatalogProduct(
                sku="SKU-1",
                name="Wireless Earbuds",
                description="Bluetooth earbuds",
                category="audio",
                brand="Sonic",
            ),
            CatalogProduct(
                sku="SKU-2",
                name="Noise Cancelling Headphones",
                description="Over-ear headset",
                category="audio",
                brand="Sonic",
            ),
        ]
        products_by_sku = {product.sku: product for product in keyword_products}

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-1", "SKU-2"])

            async def _get_product_side_effect(sku: str) -> CatalogProduct | None:
                return products_by_sku.get(sku)

            async def _get_inventory_side_effect(sku: str) -> InventoryItem:
                return InventoryItem(sku=sku, available=6, reserved=0)

            mock_products = AsyncMock()
            mock_products.get_product.side_effect = _get_product_side_effect
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(side_effect=_get_inventory_side_effect)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle(
                {
                    "query": "wireless earbuds",
                    "limit": 2,
                    "mode": "keyword",
                }
            )

            ranked_ids = [item["item_id"] for item in result["results"]]
            assert ranked_ids == ["SKU-1", "SKU-2"]
            assert mock_search.await_count == 1

    @pytest.mark.asyncio
    async def test_handle_intelligent_mode_expands_keyword_cycle_when_semantic_empty(
        self, agent_dependencies, mock_keyword_search_result
    ):
        """Intelligent mode feeds intent sub-queries to multi_query_search for hybrid retrieval."""
        expanded_product = CatalogProduct(
            sku="SKU-EARBUD",
            name="Commuter Wireless Earbuds",
            description="Low-latency earbuds for commute",
            category="audio",
            brand="TransitSound",
        )

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # Keyword search (original query) returns empty
            mock_search.return_value = AISearchSkuResult(skus=[])
            mock_kw_search.return_value = mock_keyword_search_result
            # Hybrid search finds the product via intent-derived sub-queries
            # Score higher than keyword result (1.0) so hybrid-discovered
            # product ranks first under score-based merge.
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-EARBUD",
                    score=1.20,
                    document={"sku": "SKU-EARBUD"},
                    enriched_fields={},
                )
            ]

            async def _get_product_side_effect(sku: str) -> CatalogProduct | None:
                if sku == "SKU-EARBUD":
                    return expanded_product
                return None

            async def _inventory_side_effect(sku: str) -> InventoryItem:
                return InventoryItem(sku=sku, available=9, reserved=0)

            mock_products = AsyncMock()
            mock_products.search = AsyncMock(return_value=[])
            mock_products.get_product.side_effect = _get_product_side_effect
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item.side_effect = _inventory_side_effect

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.9,
                        queryType="complex",
                        useCase="product discovery",
                        entities={
                            "keywords": ["wireless", "earbuds"],
                            "subQueries": ["wireless earbuds"],
                        },
                    )
                ),
            ):
                result = await agent.handle(
                    {
                        "query": "best earbuds for commute",
                        "limit": 3,
                        "mode": "intelligent",
                    }
                )

            ranked_ids = [item["item_id"] for item in result["results"]]
            assert ranked_ids[0] == "SKU-EARBUD"
            mock_multi.assert_awaited_once()
            # Keyword search called once for original query
            assert mock_kw_search.await_count == 1

    @pytest.mark.asyncio
    async def test_handle_inventory_lookup_error_returns_unknown_availability(
        self, agent_dependencies, mock_catalog_product
    ):
        """Inventory dependency errors should degrade to unknown availability, not 500."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=mock_catalog_product)
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(side_effect=RuntimeError("inventory unavailable"))

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "test product", "limit": 5, "mode": "keyword"})

            assert len(result["results"]) == 1
            assert result["results"][0]["item_id"] == "SKU-001"
            assert result["results"][0]["availability"] == "unknown"
            assert result["answer_source"] == "agent_fallback"

    @pytest.mark.asyncio
    async def test_handle_ai_search_product_lookup_error_returns_graceful_response(
        self, agent_dependencies
    ):
        """AI-search SKU resolution errors should return deterministic empty results, not 500."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.search_catalog_skus_detailed") as mock_search,
        ):
            mock_search.return_value = AISearchSkuResult(skus=["SKU-001"])

            mock_products = AsyncMock()
            mock_products.search = AsyncMock(return_value=[])
            mock_products.get_product = AsyncMock(side_effect=RuntimeError("product unavailable"))
            mock_products.get_related = AsyncMock(return_value=[])

            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=None)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            result = await agent.handle({"query": "travel backpack", "limit": 5, "mode": "keyword"})

            assert result["service"] == "test-catalog-search"
            assert result["query"] == "travel backpack"
            assert result["results"] == []
            assert result["answer_source"] == "agent_fallback"
            assert isinstance(result["summary"], str)
            assert isinstance(result["recommendation"], str)

    def test_build_sub_queries_from_intent_entities(self, agent_dependencies):
        """Private sub-query builder should include deduped intent entities."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        intent = IntentClassification(
            intent="semantic_search",
            confidence=0.9,
            entities={
                "category": "audio",
                "features": ["wireless", "noise cancellation"],
                "keywords": ["wireless", "travel"],
            },
        )
        sub_queries = agent.build_sub_queries("best travel headphones", intent)

        assert "best travel headphones" in sub_queries
        assert "audio" in sub_queries
        assert "wireless" in sub_queries
        assert sub_queries.count("wireless") == 1

    def test_merge_results_dedupes_and_prefers_richer_enrichment(self, agent_dependencies):
        """Private merger should dedupe by SKU and keep richest enriched payload."""
        with patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build:
            mock_build.return_value = CatalogAdapters(
                products=AsyncMock(),
                inventory=AsyncMock(),
                mapping=AcpCatalogMapper(),
            )
            agent = CatalogSearchAgent(config=agent_dependencies)

        first = AISearchDocumentResult(
            sku="SKU-1",
            score=0.82,
            document={"sku": "SKU-1"},
            enriched_fields={"use_cases": ["travel"]},
        )
        second = AISearchDocumentResult(
            sku="SKU-2",
            score=0.9,
            document={"sku": "SKU-2"},
            enriched_fields={},
        )
        duplicate_richer = AISearchDocumentResult(
            sku="SKU-1",
            score=0.8,
            document={"sku": "SKU-1"},
            enriched_fields={
                "use_cases": ["travel", "office"],
                "enriched_description": "Versatile headset.",
            },
        )

        merged = agent.merge_results([[first, second], [duplicate_richer]], limit=5)

        assert [item.sku for item in merged][:2] == ["SKU-1", "SKU-2"]
        assert merged[0].enriched_fields["enriched_description"] == "Versatile headset."


class TestIntelligentScoreBasedRanking:
    """Tests for score-based merge and ranking in _search_products_intelligent."""

    @pytest.mark.asyncio
    async def test_higher_ai_search_scores_rank_first(self, agent_dependencies):
        """Products with higher AI Search scores should appear before lower-scored ones."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # Keyword returns low-score irrelevant product first
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-PUZZLE",
                    score=0.30,
                    document={"sku": "SKU-PUZZLE", "name": "Jigsaw Puzzle Winter Scene"},
                    enriched_fields={},
                ),
            ]
            # Hybrid returns high-score relevant product
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-JACKET",
                    score=0.95,
                    document={"sku": "SKU-JACKET", "name": "Warm Winter Puffer Jacket"},
                    enriched_fields={},
                ),
            ]

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-JACKET", available=5, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.9,
                        entities={"keywords": ["winter", "jacket"]},
                    )
                ),
            ):
                result = await agent.handle(
                    {"query": "warm winter jacket", "limit": 5, "mode": "intelligent"}
                )

            ranked_ids = [r["item_id"] for r in result["results"]]
            # Jacket (score=0.95) must rank before puzzle (score=0.30)
            assert ranked_ids.index("SKU-JACKET") < ranked_ids.index("SKU-PUZZLE")

    @pytest.mark.asyncio
    async def test_products_in_both_searches_get_boosted(self, agent_dependencies):
        """A product appearing in both keyword and hybrid results should rank above one in only one."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # SKU-BOTH appears in keyword AND hybrid (hits=2)
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-BOTH",
                    score=0.70,
                    document={"sku": "SKU-BOTH", "name": "Fleece Winter Jacket"},
                    enriched_fields={},
                ),
                AISearchDocumentResult(
                    sku="SKU-KW-ONLY",
                    score=0.65,
                    document={"sku": "SKU-KW-ONLY", "name": "Winter Hat"},
                    enriched_fields={},
                ),
            ]
            # SKU-BOTH also in hybrid; SKU-HYB-ONLY only in hybrid with higher single score
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-HYB-ONLY",
                    score=0.80,
                    document={"sku": "SKU-HYB-ONLY", "name": "Thermal Gloves"},
                    enriched_fields={},
                ),
                AISearchDocumentResult(
                    sku="SKU-BOTH",
                    score=0.75,
                    document={"sku": "SKU-BOTH", "name": "Fleece Winter Jacket"},
                    enriched_fields={},
                ),
            ]

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-BOTH", available=5, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.9,
                        entities={"keywords": ["winter", "jacket"]},
                    )
                ),
            ):
                result = await agent.handle(
                    {"query": "winter jacket", "limit": 5, "mode": "intelligent"}
                )

            ranked_ids = [r["item_id"] for r in result["results"]]
            # SKU-BOTH (hits=2) must rank above single-hit products
            assert ranked_ids[0] == "SKU-BOTH"

    @pytest.mark.asyncio
    async def test_score_merge_preserves_enrichment_from_best_variant(self, agent_dependencies):
        """The merge should keep the result variant with the most enrichment data."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # Keyword has no enrichment
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-001",
                    score=0.60,
                    document={"sku": "SKU-001", "name": "Product A"},
                    enriched_fields={},
                ),
            ]
            # Hybrid has enrichment
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-001",
                    score=0.85,
                    document={"sku": "SKU-001", "name": "Product A"},
                    enriched_fields={
                        "use_cases": ["outdoor"],
                        "enriched_description": "Great for outdoor use.",
                    },
                ),
            ]

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-001", available=10, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.9,
                        entities={"keywords": ["outdoor"]},
                    )
                ),
            ):
                result = await agent.handle(
                    {"query": "outdoor gear", "limit": 5, "mode": "intelligent"}
                )

            first = result["results"][0]
            assert first["item_id"] == "SKU-001"
            # Enrichment from hybrid variant should be surfaced
            assert first["use_cases"] == ["outdoor"]
            assert first["extended_attributes"]["enriched_description"] == "Great for outdoor use."


class TestParseIntentResponse:
    """Tests for _parse_intent_response with invoker content contract."""

    def test_content_key_json_string_extracts_intent(self):
        """Invoker response with top-level 'content' JSON string is parsed."""
        response = {
            "content": '{"intent": "semantic_search", "confidence": 0.88, '
            '"queryType": "complex", "entities": {"keywords": ["laptop"]}}',
            "messages": [],
            "stream": False,
            "telemetry": {},
            "_target": "ecommerce-catalog-search-fast",
            "_model": "gpt-5-nano",
        }
        result = _parse_intent_response(response)

        assert result is not None
        assert result.intent == "semantic_search"
        assert result.confidence == 0.88
        assert result.query_type == "complex"
        assert "laptop" in result.entities["keywords"]

    def test_content_key_non_json_returns_none(self):
        """Invoker response with non-JSON content text returns None."""
        result = _parse_intent_response(
            {"content": "not valid json", "messages": [], "stream": False}
        )
        assert result is None

    def test_content_key_empty_string_falls_through(self):
        """Empty content string falls through to response dict itself."""
        result = _parse_intent_response({"content": "", "messages": [], "stream": False})
        assert result is None

    def test_direct_dict_response_still_works(self):
        """Direct dict with intent/confidence keys is still parsed correctly."""
        result = _parse_intent_response(
            {"intent": "keyword_lookup", "confidence": 0.75, "entities": {}}
        )
        assert result is not None
        assert result.intent == "keyword_lookup"
        assert result.confidence == 0.75

    def test_content_key_with_markdown_fences(self):
        """Content wrapped in markdown code fences is still parsed."""
        result = _parse_intent_response(
            {
                "content": '```json\n{"intent": "semantic_search", "confidence": 0.9}\n```',
            }
        )
        assert result is not None
        assert result.intent == "semantic_search"

    def test_output_key_fallback(self):
        """Falls back to 'output' key when 'content' is absent."""
        result = _parse_intent_response({"output": '{"intent": "browse", "confidence": 0.6}'})
        assert result is not None
        assert result.intent == "browse"


class TestIntelligentQueryRelevanceRanking:
    """Tests for query relevance ranking in intelligent mode to suppress irrelevant high-score results."""

    def test_deterministic_travel_intent_expands_retail_contexts(self):
        """Travel geography should expand into deterministic shopping context."""
        russia_intent = _deterministic_intent_policy("I'm traveling to russia, what should I buy")
        assert russia_intent.category == "clothing"
        assert russia_intent.use_case == "cold-weather travel"
        assert "winter jacket" in russia_intent.sub_queries
        assert "thermal clothing" in russia_intent.sub_queries
        assert "warm clothes" in russia_intent.sub_queries
        assert "winter boots" in russia_intent.sub_queries

        caribbean_intent = _deterministic_intent_policy("What should I buy for a Caribe vacation")
        assert caribbean_intent.use_case == "warm-weather beach travel"
        assert "beachwear" in caribbean_intent.sub_queries
        assert "sunscreen" in caribbean_intent.sub_queries
        assert "sandals" in caribbean_intent.sub_queries
        assert "swimwear" in caribbean_intent.sub_queries

    @pytest.mark.asyncio
    async def test_unrelated_high_score_results_are_outranked_by_relevant_low_score(
        self, agent_dependencies
    ):
        """Unrelated high AI Search score results should be outranked by query-grounded products."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # AI Search returns irrelevant high-scored product first
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-GROOMING",
                    score=0.95,
                    document={
                        "sku": "SKU-GROOMING",
                        "name": "Premium Grooming Kit",
                        "description": "Luxury grooming essentials",
                        "category": "Personal Care",
                    },
                    enriched_fields={},
                ),
            ]
            # Hybrid returns relevant but lower-scored travel product
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-THERMAL",
                    score=0.65,
                    document={
                        "sku": "SKU-THERMAL",
                        "name": "Thermal Underwear Set",
                        "description": "Cold weather thermal clothing for travel",
                        "category": "Clothing",
                        "tags": ["travel", "cold", "thermal"],
                    },
                    enriched_fields={},
                ),
            ]

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-THERMAL", available=10, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.9,
                        entities={"keywords": ["cold", "weather", "travel"]},
                    )
                ),
            ):
                result = await agent.handle(
                    {"query": "cold weather travel gear", "limit": 5, "mode": "intelligent"}
                )

            ranked_ids = [r["item_id"] for r in result["results"]]
            assert ranked_ids == ["SKU-THERMAL"]
            assert "SKU-GROOMING" not in ranked_ids

    @pytest.mark.asyncio
    async def test_russia_travel_cold_weather_clothing_scenario(self, agent_dependencies):
        """Russia travel query should rank cold-weather clothing above unrelated items."""
        query = "I'm traveling to russia, what should I buy"
        fallback_intent = _deterministic_intent_policy(query)

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # AI Search returns mix of relevant and irrelevant high-scored items
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-MUSIC",
                    score=0.90,
                    document={
                        "sku": "SKU-MUSIC",
                        "name": "Music Theory Book",
                        "description": "Advanced music theory textbook",
                        "category": "Books",
                    },
                    enriched_fields={},
                ),
                AISearchDocumentResult(
                    sku="SKU-DUTCH-OVEN",
                    score=0.88,
                    document={
                        "sku": "SKU-DUTCH-OVEN",
                        "name": "Cast Iron Dutch Oven",
                        "description": "Heavy duty cooking pot",
                        "category": "Kitchen",
                    },
                    enriched_fields={},
                ),
            ]
            # Hybrid includes relevant cold-weather clothing
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-WINTER-JACKET",
                    score=0.75,
                    document={
                        "sku": "SKU-WINTER-JACKET",
                        "name": "Arctic Winter Jacket",
                        "description": "Insulated jacket for freezing climates",
                        "category": "Outerwear",
                        "tags": ["winter", "cold", "jacket"],
                        "attributes": {"weather": "cold", "type": "outerwear"},
                    },
                    enriched_fields={},
                ),
                AISearchDocumentResult(
                    sku="SKU-THERMAL-SOCKS",
                    score=0.70,
                    document={
                        "sku": "SKU-THERMAL-SOCKS",
                        "name": "Merino Wool Thermal Socks",
                        "description": "Warm socks for freezing weather",
                        "category": "Clothing",
                        "tags": ["thermal", "wool", "socks", "cold"],
                    },
                    enriched_fields={},
                ),
            ]

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-WINTER-JACKET", available=5, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(return_value=fallback_intent),
            ):
                result = await agent.handle({"query": query, "limit": 8, "mode": "intelligent"})

            ranked_ids = [r["item_id"] for r in result["results"]]
            assert set(ranked_ids) == {"SKU-WINTER-JACKET", "SKU-THERMAL-SOCKS"}
            assert "SKU-MUSIC" not in ranked_ids
            assert "SKU-DUTCH-OVEN" not in ranked_ids

            sub_queries = mock_multi.await_args.kwargs["sub_queries"]
            assert "winter jacket" in sub_queries
            assert "thermal clothing" in sub_queries
            assert "warm clothes" in sub_queries
            assert "thermal socks" in sub_queries
            assert "winter boots" in sub_queries

    @pytest.mark.asyncio
    async def test_zero_overlap_unrelated_results_are_suppressed(self, agent_dependencies):
        """When AI Search returns only weak/zero-overlap results, relevance ranking should suppress them."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            # AI Search returns completely unrelated high-scored items
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-PUZZLE",
                    score=0.92,
                    document={
                        "sku": "SKU-PUZZLE",
                        "name": "1000 Piece Jigsaw Puzzle",
                        "description": "Beautiful landscape puzzle",
                        "category": "Toys",
                    },
                    enriched_fields={},
                ),
            ]
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-CANDLE",
                    score=0.89,
                    document={
                        "sku": "SKU-CANDLE",
                        "name": "Lavender Scented Candle",
                        "description": "Aromatherapy candle for relaxation",
                        "category": "Home Decor",
                    },
                    enriched_fields={},
                ),
            ]

            mock_products = AsyncMock()
            mock_products.search = AsyncMock(return_value=[])
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-PUZZLE", available=3, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.8,
                        entities={"keywords": ["laptop", "computer", "technology"]},
                    )
                ),
            ):
                result = await agent.handle(
                    {"query": "laptop computer programming", "limit": 5, "mode": "intelligent"}
                )

            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_zero_overlap_baseline_is_not_returned_without_expansion(
        self, agent_dependencies
    ):
        """A no-extra-subquery fallback must not leak unrelated baseline results."""
        query = "what should I buy"

        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-PUZZLE",
                    score=0.93,
                    document={
                        "sku": "SKU-PUZZLE",
                        "name": "Jigsaw Puzzle",
                        "description": "Quiet indoor puzzle activity",
                        "category": "Toys",
                    },
                    enriched_fields={},
                )
            ]
            mock_multi.return_value = [
                AISearchDocumentResult(
                    sku="SKU-CANDLE",
                    score=0.91,
                    document={
                        "sku": "SKU-CANDLE",
                        "name": "Lavender Candle",
                        "description": "Scented candle for home decor",
                        "category": "Home Decor",
                    },
                    enriched_fields={},
                )
            ]

            mock_products = AsyncMock()
            mock_products.search = AsyncMock(return_value=[])
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(return_value=None)

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.8,
                        entities={},
                    )
                ),
            ):
                result = await agent.handle({"query": query, "limit": 5, "mode": "intelligent"})

            assert result["results"] == []
            mock_products.search.assert_awaited_once_with(query=query, limit=5)

    @pytest.mark.asyncio
    async def test_keyword_enriched_fields_survive_relevance_filter(self, agent_dependencies):
        """Enrichment from surviving keyword results should be preserved."""
        with (
            patch("ecommerce_catalog_search.agents.build_catalog_adapters") as mock_build,
            patch("ecommerce_catalog_search.agents.multi_query_search") as mock_multi,
            patch("ecommerce_catalog_search.agents.keyword_search") as mock_kw_search,
        ):
            mock_kw_search.return_value = [
                AISearchDocumentResult(
                    sku="SKU-HEADPHONES",
                    score=0.94,
                    document={
                        "sku": "SKU-HEADPHONES",
                        "name": "Travel Headphones Pro",
                        "description": "Noise-canceling headphones for travel",
                        "category": "Audio",
                    },
                    enriched_fields={
                        "use_cases": ["travel", "commute"],
                        "enriched_description": "Noise-canceling headphones for travel.",
                    },
                )
            ]
            mock_multi.return_value = []

            mock_products = AsyncMock()
            mock_products.get_product = AsyncMock(return_value=None)
            mock_products.get_related = AsyncMock(return_value=[])
            mock_inventory = AsyncMock()
            mock_inventory.get_item = AsyncMock(
                return_value=InventoryItem(sku="SKU-HEADPHONES", available=7, reserved=0)
            )

            mock_build.return_value = CatalogAdapters(
                products=mock_products,
                inventory=mock_inventory,
                mapping=AcpCatalogMapper(),
            )

            agent = CatalogSearchAgent(config=agent_dependencies)
            with patch.object(
                agent,
                "classify_intent",
                new=AsyncMock(
                    return_value=IntentClassification(
                        intent="semantic_search",
                        confidence=0.9,
                        entities={"keywords": ["travel", "headphones"]},
                    )
                ),
            ):
                result = await agent.handle(
                    {"query": "travel headphones", "limit": 5, "mode": "intelligent"}
                )

            assert result["results"][0]["item_id"] == "SKU-HEADPHONES"
            assert result["results"][0]["use_cases"] == ["travel", "commute"]
            assert result["results"][0]["extended_attributes"]["enriched_description"].startswith(
                "Noise-canceling"
            )
