"""Base agent abstraction."""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from agent_framework import Agent


class BaseRetailAgent(Agent, ABC):
    """Common ingestion, routing, and memory ops."""

    def __init__(self, router: Any, tools: Optional[Dict[str, Callable[..., Any]]] = None) -> None:
        super().__init__()
        self.router = router
        self.tools = tools or {}
        self.hot_memory = None
        self.warm_memory = None
        self.cold_memory = None
        self.mcp_server = None

    def attach_memory(self, hot: Any, warm: Any, cold: Any) -> None:
        self.hot_memory = hot
        self.warm_memory = warm
        self.cold_memory = cold

    def attach_mcp(self, mcp_server: Any) -> None:
        self.mcp_server = mcp_server

    @abstractmethod
    async def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming request."""
