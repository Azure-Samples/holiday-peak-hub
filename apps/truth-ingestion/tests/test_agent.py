"""Unit tests for TruthIngestionAgent."""

from __future__ import annotations

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies
from truth_ingestion.agent import TruthIngestionAgent


@pytest.fixture
def agent_config():
    return AgentDependencies(
        service_name="truth-ingestion-test",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


@pytest.fixture
def agent(agent_config, mock_adapters):
    a = TruthIngestionAgent(agent_config)
    a._adapters = mock_adapters
    return a


class TestTruthIngestionAgent:
    @pytest.mark.asyncio
    async def test_ingest_single_action(self, agent, sample_pim_product):
        result = await agent.handle({"action": "ingest_single", "product": sample_pim_product})
        assert result["action"] == "ingest_single"
        assert result["result"]["entity_id"] == "PROD-001"

    @pytest.mark.asyncio
    async def test_ingest_single_missing_product(self, agent):
        result = await agent.handle({"action": "ingest_single"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ingest_bulk_action(
        self, agent, sample_pim_product, sample_pim_product_no_variants
    ):
        result = await agent.handle(
            {
                "action": "ingest_bulk",
                "products": [sample_pim_product, sample_pim_product_no_variants],
            }
        )
        assert result["action"] == "ingest_bulk"
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_ingest_bulk_missing_products(self, agent):
        result = await agent.handle({"action": "ingest_bulk"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_status_found(self, agent, mock_adapters):
        from unittest.mock import AsyncMock

        from truth_ingestion.adapters import ProductStyle

        style = ProductStyle(entity_id="PROD-001", name="Hat", category="c", brand="b")
        mock_adapters.truth_store.get_product_style = AsyncMock(return_value=style.to_dict())
        result = await agent.handle({"action": "get_status", "entity_id": "PROD-001"})
        assert result["found"] is True
        assert result["entity_id"] == "PROD-001"

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, agent, mock_adapters):
        from unittest.mock import AsyncMock

        mock_adapters.truth_store.get_product_style = AsyncMock(return_value=None)
        result = await agent.handle({"action": "get_status", "entity_id": "MISSING"})
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_get_status_missing_entity_id(self, agent):
        result = await agent.handle({"action": "get_status"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_default_action_is_ingest_single(self, agent, sample_pim_product):
        """No explicit action defaults to ingest_single."""
        result = await agent.handle({"product": sample_pim_product})
        assert result["action"] == "ingest_single"
