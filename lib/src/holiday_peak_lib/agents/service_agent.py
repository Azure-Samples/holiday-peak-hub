"""Generic service agent implementation."""
from typing import Any

from .base_agent import BaseRetailAgent


class ServiceAgent(BaseRetailAgent):
    """Default service agent that echoes the payload with service metadata."""

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"service": self.service_name or "", "received": request}
