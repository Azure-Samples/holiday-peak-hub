"""MCP tool modules shared across services."""

from holiday_peak_lib.mcp.ai_search_indexing import (
    AISearchIndexingClient,
    build_ai_search_indexing_client_from_env,
    register_ai_search_indexing_tools,
)
from holiday_peak_lib.mcp.server import FastAPIMCPServer, MCPToolSchemaRef

__all__ = [
    "AISearchIndexingClient",
    "build_ai_search_indexing_client_from_env",
    "register_ai_search_indexing_tools",
    "FastAPIMCPServer",
    "MCPToolSchemaRef",
]
