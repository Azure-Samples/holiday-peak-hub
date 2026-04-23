"""Shared MCP tool registration helpers used by all agent services.

The former ``register_crud_tools`` helper was removed as part of the agent
isolation initiative (ADR-036). Agents are now strictly forbidden from calling
the CRUD service directly; peer-to-peer agent communication happens over the
Azure API Management MCP surface, and async flows happen through Event Hubs
published/consumed via the ``holiday_peak_lib.messaging`` Observer helpers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

if __name__ != "__main__":  # pragma: no cover – TYPE_CHECKING alternative
    from holiday_peak_lib.agents import BaseRetailAgent


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
