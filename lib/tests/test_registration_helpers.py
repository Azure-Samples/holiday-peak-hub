"""Tests for shared MCP registration helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    mcp_context_tool,
    register_crud_tools,
)


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


class TestRegisterCrudTools:
    def test_no_op_when_env_not_set(self) -> None:
        mcp = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            register_crud_tools(mcp)
        mcp.add_tool.assert_not_called()
