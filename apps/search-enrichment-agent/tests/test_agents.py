"""Unit tests for SearchEnrichmentAgent orchestration and MCP registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies, ModelTarget
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.utils.telemetry import get_foundry_tracer
from search_enrichment_agent.adapters import SearchEnrichmentAdapters
from search_enrichment_agent.agents import SearchEnrichmentAgent, register_mcp_tools

_TRACE_SERVICE_NAME = "search-enrichment-agent-test"


@pytest.fixture(autouse=True)
def _clear_service_traces() -> None:
    get_foundry_tracer(_TRACE_SERVICE_NAME).clear()


def _trace_events(*, event_type: str, name: str) -> list[dict[str, object]]:
    return [
        event
        for event in get_foundry_tracer(_TRACE_SERVICE_NAME).get_traces(limit=100)
        if event.get("type") == event_type and event.get("name") == name
    ]


def _build_agent_config_with_slm() -> AgentDependencies:
    async def dummy_invoker(**kwargs):  # noqa: ANN003
        _ = kwargs.get("messages")
        _ = kwargs.get("tools")
        return {"enriched_description": "dummy", "search_keywords": ["dummy"]}

    slm = ModelTarget(name="slm", model="fast-model", invoker=dummy_invoker)
    return AgentDependencies(
        service_name=_TRACE_SERVICE_NAME,
        router=None,
        tools={},
        slm=slm,
        llm=None,
    )


def _build_agent_config_without_models() -> AgentDependencies:
    return AgentDependencies(
        service_name=_TRACE_SERVICE_NAME,
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


def _mock_adapters() -> SearchEnrichmentAdapters:
    approved_truth = AsyncMock()
    approved_truth.get_approved_data = AsyncMock(
        return_value={
            "sku": "SKU-1",
            "name": "Trail Shoe",
            "category": "shoe",
            "description": "Daily running trail shoe",
            "brand": "Peak",
        }
    )

    enriched_store = AsyncMock()
    enriched_store.upsert = AsyncMock(side_effect=lambda payload: payload)
    enriched_store.get_status = AsyncMock(return_value={"entity_id": "SKU-1", "status": "upserted"})

    foundry = AsyncMock()
    foundry.set_model_invoker = Mock()
    foundry.enrich_complex_fields = AsyncMock(return_value={"_status": "fallback"})

    return SearchEnrichmentAdapters(
        approved_truth=approved_truth,
        enriched_store=enriched_store,
        foundry=foundry,
    )


@pytest.mark.asyncio
async def test_handle_requires_entity_id() -> None:
    agent_config_without_models = _build_agent_config_without_models()
    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters",
        return_value=_mock_adapters(),
    ):
        agent = SearchEnrichmentAgent(config=agent_config_without_models)

    result = await agent.handle({})
    assert result["error"] == "entity_id is required"
    liveness_events = _trace_events(event_type="decision", name="liveness.api.invoke")
    assert len(liveness_events) == 1
    assert liveness_events[0]["outcome"] == "missing_entity_id"
    assert liveness_events[0]["metadata"] == {
        "surface": "api",
        "trigger": "invoke",
        "endpoint": "/invoke",
        "status": "error",
    }


@pytest.mark.asyncio
async def test_handle_enriches_with_simple_strategy_when_models_unavailable() -> None:
    agent_config_without_models = _build_agent_config_without_models()
    adapters = _mock_adapters()
    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters", return_value=adapters
    ):
        agent = SearchEnrichmentAgent(config=agent_config_without_models)

    result = await agent.handle({"entity_id": "SKU-1"})

    assert result["status"] == "enriched"
    assert result["strategy"] == "simple"
    assert result["container"] == "search_enriched_products"
    assert "search_keywords" in result["enriched"]["enrichedData"]
    liveness_events = _trace_events(event_type="decision", name="liveness.api.invoke")
    assert len(liveness_events) == 1
    assert liveness_events[0]["outcome"] == "enriched"
    assert liveness_events[0]["metadata"] == {
        "surface": "api",
        "trigger": "invoke",
        "endpoint": "/invoke",
        "entity_id": "SKU-1",
        "status": "enriched",
    }


@pytest.mark.asyncio
async def test_register_mcp_tools_adds_required_paths() -> None:
    agent_config_with_slm = _build_agent_config_with_slm()
    mcp = Mock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):  # noqa: ANN001
        mcp.tools[path] = handler

    mcp.add_tool = add_tool

    adapters = _mock_adapters()
    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters", return_value=adapters
    ):
        agent = SearchEnrichmentAgent(config=agent_config_with_slm)
        register_mcp_tools(mcp, agent)

    assert "/search-enrichment/enrich" in mcp.tools
    assert "/search-enrichment/status" in mcp.tools

    enrich_tool = mcp.tools["/search-enrichment/enrich"]
    status_tool = mcp.tools["/search-enrichment/status"]

    enrich_result = await enrich_tool({"entity_id": "SKU-1"})
    status_result = await status_tool({"entity_id": "SKU-1"})

    assert enrich_result["status"] == "enriched"
    assert status_result["status"] == "upserted"
    enrich_liveness = _trace_events(event_type="tool_call", name="/search-enrichment/enrich")
    assert len(enrich_liveness) == 1
    assert enrich_liveness[0]["outcome"] == "enriched"
    assert enrich_liveness[0]["metadata"] == {
        "surface": "mcp",
        "trigger": "mcp",
        "endpoint": "/search-enrichment/enrich",
        "entity_id": "SKU-1",
        "status": "enriched",
    }

    status_liveness = _trace_events(event_type="tool_call", name="/search-enrichment/status")
    assert len(status_liveness) == 1
    assert status_liveness[0]["outcome"] == "upserted"
    assert status_liveness[0]["metadata"] == {
        "surface": "mcp",
        "trigger": "mcp",
        "endpoint": "/search-enrichment/status",
        "entity_id": "SKU-1",
        "status": "upserted",
    }


@pytest.mark.asyncio
async def test_register_mcp_tools_traces_missing_entity_id_paths() -> None:
    agent_config_with_slm = _build_agent_config_with_slm()
    mcp = Mock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):  # noqa: ANN001
        mcp.tools[path] = handler

    mcp.add_tool = add_tool

    adapters = _mock_adapters()
    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters", return_value=adapters
    ):
        agent = SearchEnrichmentAgent(config=agent_config_with_slm)
        register_mcp_tools(mcp, agent)

    enrich_tool = mcp.tools["/search-enrichment/enrich"]
    status_tool = mcp.tools["/search-enrichment/status"]

    enrich_result = await enrich_tool({})
    status_result = await status_tool({})

    assert enrich_result["error"] == "entity_id is required"
    assert status_result["error"] == "entity_id is required"

    enrich_liveness = _trace_events(event_type="tool_call", name="/search-enrichment/enrich")
    assert len(enrich_liveness) == 1
    assert enrich_liveness[0]["outcome"] == "missing_entity_id"
    assert enrich_liveness[0]["metadata"] == {
        "surface": "mcp",
        "trigger": "mcp",
        "endpoint": "/search-enrichment/enrich",
        "status": "error",
    }

    status_liveness = _trace_events(event_type="tool_call", name="/search-enrichment/status")
    assert len(status_liveness) == 1
    assert status_liveness[0]["outcome"] == "missing_entity_id"
    assert status_liveness[0]["metadata"] == {
        "surface": "mcp",
        "trigger": "mcp",
        "endpoint": "/search-enrichment/status",
        "status": "error",
    }


@pytest.mark.asyncio
async def test_register_mcp_tools_traces_error_when_handler_raises() -> None:
    agent_config_with_slm = _build_agent_config_with_slm()
    mcp = Mock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):  # noqa: ANN001
        mcp.tools[path] = handler

    mcp.add_tool = add_tool

    adapters = _mock_adapters()
    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters", return_value=adapters
    ):
        agent = SearchEnrichmentAgent(config=agent_config_with_slm)
        with patch.object(agent, "enrich", AsyncMock(side_effect=RuntimeError("mcp boom"))):
            register_mcp_tools(mcp, agent)
            enrich_tool = mcp.tools["/search-enrichment/enrich"]

            with pytest.raises(RuntimeError, match="mcp boom"):
                await enrich_tool({"entity_id": "SKU-1"})

    liveness_events = _trace_events(event_type="tool_call", name="/search-enrichment/enrich")
    assert len(liveness_events) == 1
    assert liveness_events[0]["outcome"] == "error"
    assert liveness_events[0]["metadata"] == {
        "surface": "mcp",
        "trigger": "mcp",
        "endpoint": "/search-enrichment/enrich",
        "entity_id": "SKU-1",
        "status": "error",
    }


@pytest.mark.asyncio
async def test_enrich_triggers_search_indexing_after_upsert() -> None:
    agent_config_without_models = _build_agent_config_without_models()
    adapters = _mock_adapters()
    adapters.search_indexing = AsyncMock()
    adapters.search_indexing.sync_after_upsert = AsyncMock(return_value={"status": "accepted"})

    with patch(
        "search_enrichment_agent.agents.build_search_enrichment_adapters", return_value=adapters
    ):
        agent = SearchEnrichmentAgent(config=agent_config_without_models)

    result = await agent.enrich("SKU-1", trigger="test")

    adapters.search_indexing.sync_after_upsert.assert_awaited_once()
    assert result["indexing"]["status"] == "accepted"


@pytest.mark.asyncio
async def test_register_mcp_tools_adds_ai_search_indexing_paths_when_configured() -> None:
    agent_config_with_slm = _build_agent_config_with_slm()
    mcp = Mock(spec=FastAPIMCPServer)
    mcp.tools = {}

    def add_tool(path, handler):  # noqa: ANN001
        mcp.tools[path] = handler

    mcp.add_tool = add_tool

    fake_client = object()
    adapters = _mock_adapters()
    with (
        patch(
            "search_enrichment_agent.agents.build_search_enrichment_adapters", return_value=adapters
        ),
        patch(
            "search_enrichment_agent.agents.build_ai_search_indexing_client_from_env",
            return_value=fake_client,
        ),
        patch("search_enrichment_agent.agents.register_ai_search_indexing_tools") as register_tools,
    ):
        agent = SearchEnrichmentAgent(config=agent_config_with_slm)
        register_mcp_tools(mcp, agent)

    register_tools.assert_called_once_with(mcp, client=fake_client)
