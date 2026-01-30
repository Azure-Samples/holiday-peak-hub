"""Agent client for optional MCP tool invocation."""

import asyncio
import logging
from typing import Any

import httpx

from crud_service.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentClient:
    """
    Client for invoking agent MCP tools with timeout and fallback.
    
    Used for optional agent calls (e.g., personalization, recommendations).
    If agent is unavailable or times out, fallback to basic logic.
    """

    def __init__(self):
        self.timeout = settings.agent_timeout_seconds
        self.enable_fallback = settings.enable_agent_fallback

    async def invoke_tool(
        self,
        agent_url: str,
        tool_name: str,
        parameters: dict[str, Any],
        fallback_value: Any = None,
    ) -> Any:
        """
        Invoke an agent MCP tool with timeout.
        
        Args:
            agent_url: Agent service URL (e.g., "http://crm-profile-aggregation/mcp")
            tool_name: MCP tool name (e.g., "get_user_context")
            parameters: Tool parameters
            fallback_value: Value to return if agent unavailable
            
        Returns:
            Tool response or fallback_value if agent unavailable
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{agent_url}/{tool_name}",
                    json=parameters,
                )
                response.raise_for_status()
                return response.json()

        except (httpx.TimeoutException, httpx.HTTPError) as e:
            logger.warning(
                f"Agent call failed: {agent_url}/{tool_name} - {e}. "
                f"Using fallback: {fallback_value}"
            )
            if self.enable_fallback:
                return fallback_value
            raise

    async def get_user_recommendations(
        self, user_id: str, category: str | None = None
    ) -> list[str]:
        """
        Get product recommendations from CRM agent.
        
        Fallback: Return empty list if agent unavailable.
        """
        try:
            result = await self.invoke_tool(
                agent_url="http://crm-profile-aggregation/mcp",
                tool_name="get_recommendations",
                parameters={"user_id": user_id, "category": category},
                fallback_value={"product_ids": []},
            )
            return result.get("product_ids", [])
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []

    async def calculate_dynamic_pricing(
        self, product_id: str, user_id: str | None = None
    ) -> float | None:
        """
        Get dynamic pricing from pricing agent.
        
        Fallback: Return None (use base price).
        """
        try:
            result = await self.invoke_tool(
                agent_url="http://pricing-optimization/mcp",
                tool_name="calculate_price",
                parameters={"product_id": product_id, "user_id": user_id},
                fallback_value=None,
            )
            return result.get("price") if result else None
        except Exception as e:
            logger.error(f"Failed to calculate dynamic pricing: {e}")
            return None

    async def get_inventory_status(self, product_id: str) -> dict:
        """
        Get inventory status from inventory agent.
        
        Fallback: Return unknown status.
        """
        try:
            result = await self.invoke_tool(
                agent_url="http://inventory-health-check/mcp",
                tool_name="check_availability",
                parameters={"product_id": product_id},
                fallback_value={"available": True, "quantity": 999},
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get inventory status: {e}")
            return {"available": True, "quantity": 999}


# Global instance
_agent_client: AgentClient | None = None


def get_agent_client() -> AgentClient:
    """Get global agent client instance."""
    global _agent_client
    if _agent_client is None:
        _agent_client = AgentClient()
    return _agent_client
