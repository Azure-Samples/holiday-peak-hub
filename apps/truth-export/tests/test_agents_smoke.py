"""Smoke tests for TruthExportAgent behavior."""

# pylint: disable=protected-access,redefined-outer-name

from __future__ import annotations

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies
from truth_export.adapters import build_truth_export_adapters
from truth_export.agents import TruthExportAgent
from truth_export.schemas_compat import ProductStyle


@pytest.fixture()
def agent() -> TruthExportAgent:
    dependencies = AgentDependencies(
        service_name="truth-export-test",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )
    instance = TruthExportAgent(dependencies)
    instance._adapters = build_truth_export_adapters()
    return instance


@pytest.mark.asyncio
async def test_handle_requires_entity_id(agent: TruthExportAgent) -> None:
    result = await agent.handle({})
    assert result["error"] == "entity_id is required"


@pytest.mark.asyncio
async def test_handle_returns_not_found_for_missing_product(agent: TruthExportAgent) -> None:
    result = await agent.handle({"entity_id": "STYLE-404", "protocol": "ucp"})
    assert result["error"] == "product not found"
    assert result["entity_id"] == "STYLE-404"


@pytest.mark.asyncio
async def test_handle_exports_seeded_product(agent: TruthExportAgent) -> None:
    agent.adapters.truth_store.seed_style(
        ProductStyle(
            id="STYLE-100",
            brand="Contoso",
            modelName="Explorer",
            categoryId="footwear",
        )
    )

    result = await agent.handle({"entity_id": "STYLE-100", "protocol": "ucp"})

    assert result["entity_id"] == "STYLE-100"
    assert result["protocol"] == "ucp"
    assert result["status"] == "completed"
