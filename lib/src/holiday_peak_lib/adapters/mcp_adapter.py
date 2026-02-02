"""MCP adapter registry utilities."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class BaseMCPAdapter:
    """Base adapter that registers MCP tools with a FastAPI MCP server."""

    def __init__(self, name: str, *, tool_prefix: str = "") -> None:
        self.name = name
        self._tool_prefix = tool_prefix.rstrip("/")
        self._tools: list[tuple[str, ToolHandler]] = []

    @property
    def tools(self) -> tuple[tuple[str, ToolHandler], ...]:
        """Return registered tool paths and handlers."""
        return tuple(self._tools)

    def add_tool(self, path: str, handler: ToolHandler) -> None:
        """Register a tool handler for MCP exposure."""
        normalized = self._normalize_path(path)
        self._tools.append((normalized, handler))

    def register_mcp_tools(self, mcp: FastAPIMCPServer) -> None:
        """Register all tools with the provided MCP server."""
        for path, handler in self._tools:
            mcp.add_tool(path, handler)

    def _normalize_path(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        if self._tool_prefix:
            return f"{self._tool_prefix}{path}"
        return path
