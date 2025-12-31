"""Thin wrapper to expose MCP endpoints over FastAPI."""
from fastapi import APIRouter, FastAPI


class FastAPIMCPServer:
    """Registers MCP routes on a FastAPI app."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.router = APIRouter()

    def add_tool(self, path: str, handler) -> None:
        self.router.post(path)(handler)

    def mount(self) -> None:
        self.app.include_router(self.router, prefix="/mcp")
