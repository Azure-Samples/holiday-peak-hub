"""Tests for shared MCP registration helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from holiday_peak_lib.agents.registration_helpers import (
    _sanitize_tool_name,
    bind_mcp_tools_as_function_tools,
    build_named_function_tool,
    get_agent_adapters,
    mcp_context_tool,
)
from holiday_peak_lib.mcp.server import FastAPIMCPServer


class TestGetAgentAdapters:
    def test_returns_agent_adapters_when_present(self) -> None:
        agent = MagicMock()
        agent.adapters = "real_adapters"
        fallback = MagicMock(return_value="fallback_adapters")
        result = get_agent_adapters(agent, fallback)
        assert result == "real_adapters"
        fallback.assert_not_called()

    def test_returns_fallback_when_no_adapters(self) -> None:
        agent = MagicMock(spec=[])  # no attributes
        fallback = MagicMock(return_value="fallback_adapters")
        result = get_agent_adapters(agent, fallback)
        assert result == "fallback_adapters"
        fallback.assert_called_once()


class TestMcpContextTool:
    @pytest.mark.asyncio
    async def test_returns_error_when_id_missing(self) -> None:
        adapter_method = AsyncMock()
        handler = mcp_context_tool(
            adapter_method,
            id_param="sku",
            result_key="inventory_context",
        )
        result = await handler({})
        assert result == {"error": "sku is required"}
        adapter_method.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_context_model_dump(self) -> None:
        context = MagicMock()
        context.model_dump.return_value = {"sku": "A1", "available": 10}
        adapter_method = AsyncMock(return_value=context)

        handler = mcp_context_tool(
            adapter_method,
            id_param="sku",
            result_key="inventory_context",
        )
        result = await handler({"sku": "A1"})

        adapter_method.assert_awaited_once_with("A1")
        assert result == {"inventory_context": {"sku": "A1", "available": 10}}

    @pytest.mark.asyncio
    async def test_returns_none_when_context_is_none(self) -> None:
        adapter_method = AsyncMock(return_value=None)

        handler = mcp_context_tool(
            adapter_method,
            id_param="tracking_id",
            result_key="logistics_context",
        )
        result = await handler({"tracking_id": "T-123"})

        assert result == {"logistics_context": None}

    @pytest.mark.asyncio
    async def test_casts_id_to_string(self) -> None:
        adapter_method = AsyncMock(return_value=None)

        handler = mcp_context_tool(
            adapter_method,
            id_param="sku",
            result_key="ctx",
        )
        await handler({"sku": 42})

        adapter_method.assert_awaited_once_with("42")


class TestSanitizeToolName:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("/inventory/health/context", "inventory_health_context"),
            ("/inventory/health", "inventory_health"),
            ("ecommerce-checkout-support", "ecommerce_checkout_support"),
            ("//a//b//", "a_b"),
            ("", "tool"),
            ("/", "tool"),
            ("123abc", "t_123abc"),
        ],
    )
    def test_sanitizes_to_valid_identifier(self, raw: str, expected: str) -> None:
        result = _sanitize_tool_name(raw)
        assert result == expected
        assert result.isidentifier()


class TestBuildNamedFunctionTool:
    @pytest.mark.asyncio
    async def test_carries_name_and_doc_and_awaits_async_handler(self) -> None:
        async def handler(payload: dict[str, Any]) -> dict[str, Any]:
            return {"echo": payload.get("v")}

        tool = build_named_function_tool("inventory_health", "Check health", handler)
        assert tool.__name__ == "inventory_health"
        assert tool.__doc__ == "Check health"
        assert await tool({"v": 7}) == {"echo": 7}

    @pytest.mark.asyncio
    async def test_wraps_sync_handler_and_non_dict_result(self) -> None:
        def handler(payload: dict[str, Any]) -> str:
            return "ok"

        tool = build_named_function_tool("t", "", handler)
        assert tool.__doc__ == "Invoke the t operation."
        assert await tool({}) == {"result": "ok"}


class TestBindMcpToolsAsFunctionTools:
    @pytest.mark.asyncio
    async def test_binds_registered_mcp_tools_as_named_model_tools(self) -> None:
        app = FastAPI()
        mcp = FastAPIMCPServer(app)

        async def get_context(payload: dict[str, Any]) -> dict[str, Any]:
            return {"context": payload.get("sku")}

        async def get_health(payload: dict[str, Any]) -> dict[str, Any]:
            return {"healthy": True}

        mcp.add_tool(
            "/inventory/health/context", get_context, metadata={"description": "Fetch ctx"}
        )
        mcp.add_tool("/inventory/health", get_health)

        agent = MagicMock()
        bound = bind_mcp_tools_as_function_tools(agent, mcp)

        assert set(bound) == {"inventory_health_context", "inventory_health"}
        # The binder assigns the mapping to ``agent.tools`` (a dict of callables)
        # which the base agent forwards to the direct-model invoker per call.
        assert agent.tools == bound
        assert bound["inventory_health_context"].__doc__ == "Fetch ctx"
        # The named wrapper still calls the original handler implementation.
        assert await bound["inventory_health_context"]({"sku": "A1"}) == {"context": "A1"}
        assert await bound["inventory_health"]({}) == {"healthy": True}

    def test_returns_empty_when_no_tools_registered(self) -> None:
        app = FastAPI()
        mcp = FastAPIMCPServer(app)
        agent = MagicMock()
        assert bind_mcp_tools_as_function_tools(agent, mcp) == {}

    def test_deduplicates_colliding_sanitized_names(self) -> None:
        app = FastAPI()
        mcp = FastAPIMCPServer(app)

        async def h(payload: dict[str, Any]) -> dict[str, Any]:
            return {}

        # ``/a/b`` and ``/a-b`` both sanitize to ``a_b`` — the binder must keep
        # both as distinct function names so the model can target each.
        mcp.add_tool("/a/b", h)
        mcp.add_tool("/a-b", h)
        agent = MagicMock()
        bound = bind_mcp_tools_as_function_tools(agent, mcp)
        assert len(bound) == 2
        assert "a_b" in bound
        assert any(name != "a_b" and name.startswith("a_b") for name in bound)
