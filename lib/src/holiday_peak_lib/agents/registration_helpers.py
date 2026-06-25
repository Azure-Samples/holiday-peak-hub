"""Shared MCP tool registration helpers used by all agent services.

The former ``register_crud_tools`` helper was removed as part of the agent
isolation initiative (ADR-036). Agents are now strictly forbidden from calling
the CRUD service directly; peer-to-peer agent communication happens over the
Azure API Management MCP surface, and async flows happen through Event Hubs
published/consumed via the ``holiday_peak_lib.messaging`` Observer helpers.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from inspect import isawaitable
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


_TOOL_NAME_SANITIZE = re.compile(r"[^0-9a-zA-Z_]+")


def _sanitize_tool_name(raw: str) -> str:
    """Turn an MCP path/name into a valid function-tool identifier.

    ``/inventory/health/context`` -> ``inventory_health_context``. The model
    selects and calls tools by this name, so it must be a clean identifier:
    no slashes, no leading digit, no doubled or trailing underscores.
    """
    cleaned = _TOOL_NAME_SANITIZE.sub("_", raw.strip().strip("/"))
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        return "tool"
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned


def build_named_function_tool(
    name: str,
    description: str,
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]],
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Wrap an MCP handler as a named async callable for MAF function-calling.

    The Microsoft Agent Framework derives a tool's function name, description,
    and schema from the callable's ``__name__``, ``__doc__``, and signature.
    MCP handlers are anonymous closures over a generic ``payload`` dict, so we
    wrap each one in a freshly-named coroutine carrying the tool name and
    description the model needs to choose and invoke it.
    """

    async def _tool(payload: dict[str, Any]) -> dict[str, Any]:
        outcome = handler(payload)
        if isawaitable(outcome):
            outcome = await outcome
        return outcome if isinstance(outcome, dict) else {"result": outcome}

    _tool.__name__ = name
    _tool.__qualname__ = name
    _tool.__doc__ = description or f"Invoke the {name} operation."
    return _tool


def bind_mcp_tools_as_function_tools(
    agent: "BaseRetailAgent",
    mcp: Any,
) -> dict[str, Callable[..., Any]]:
    """Expose an agent's registered MCP tools to its model as function tools.

    Reads the raw handlers from ``mcp.tool_handlers`` and descriptions from
    ``mcp.tool_metadata``, builds one named coroutine per tool, and assigns the
    resulting ``{name: callable}`` mapping to ``agent.tools``. The base agent
    forwards ``agent.tools`` to the direct-model invoker on every call, so the
    model emits real ``function_call``/``function_result`` turns instead of a
    single tool-less completion. Returns the bound mapping (empty when the
    agent registered no MCP tools).
    """
    handlers = getattr(mcp, "tool_handlers", {})
    if not handlers:
        return {}
    metadata = getattr(mcp, "tool_metadata", {})
    function_tools: dict[str, Callable[..., Any]] = {}
    used: set[str] = set()
    for path, handler in handlers.items():
        details = metadata.get(path, {}) if isinstance(metadata, dict) else {}
        raw_name = str(details.get("name") or path)
        tool_name = _sanitize_tool_name(raw_name)
        # De-duplicate identifiers that collide after sanitization so every
        # tool keeps a distinct function name the model can target.
        if tool_name in used:
            suffix = 2
            while f"{tool_name}_{suffix}" in used:
                suffix += 1
            tool_name = f"{tool_name}_{suffix}"
        used.add(tool_name)
        meta_block = details.get("metadata") if isinstance(details, dict) else None
        description = ""
        if isinstance(meta_block, dict):
            description = str(meta_block.get("description") or meta_block.get("summary") or "")
        function_tools[tool_name] = build_named_function_tool(tool_name, description, handler)
    if function_tools:
        agent.tools = function_tools
    return function_tools
