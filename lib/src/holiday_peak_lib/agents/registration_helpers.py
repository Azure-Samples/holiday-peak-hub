"""Shared MCP tool registration helpers used by all agent services."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.mcp.server import FastAPIMCPServer

if __name__ != "__main__":  # pragma: no cover – TYPE_CHECKING alternative
    from holiday_peak_lib.agents import BaseRetailAgent


def register_crud_tools(mcp: FastAPIMCPServer) -> None:
    """Register CRUD adapter MCP tools if ``CRUD_SERVICE_URL`` is set.

    This replaces the identical ``_register_crud_tools()`` function that was
    previously copy-pasted into every ``agents.py`` across all app services.
    """
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def get_agent_adapters(
    agent: BaseRetailAgent,
    fallback_factory: Callable[[], Any],
) -> Any:
    """Resolve adapters from an agent instance, falling back to a factory."""
    adapters = getattr(agent, "adapters", None)
    if adapters is not None:
        return adapters
    return fallback_factory()


def mcp_context_tool(
    adapter_method: Callable[..., Awaitable[Any]],
    *,
    id_param: str,
    result_key: str,
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Create a simple MCP context-fetch tool.

    Replaces the boilerplate pattern::

        async def get_X_context(payload):
            id_val = payload.get("id_param")
            if not id_val:
                return {"error": "id_param is required"}
            context = await adapter_method(str(id_val))
            return {"result_key": context.model_dump() if context else None}
    """

    async def handler(payload: dict[str, Any]) -> dict[str, Any]:
        id_val = payload.get(id_param)
        if not id_val:
            return {"error": f"{id_param} is required"}
        context = await adapter_method(str(id_val))
        return {result_key: context.model_dump() if context else None}

    return handler
