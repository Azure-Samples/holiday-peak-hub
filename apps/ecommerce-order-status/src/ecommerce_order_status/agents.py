"""Order status agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import OrderStatusAdapters, build_order_status_adapters


class OrderStatusAgent(BaseRetailAgent):
    """Agent that provides order status insights."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_order_status_adapters()

    @property
    def adapters(self) -> OrderStatusAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        order_id = request.get("order_id")
        tracking_id = request.get("tracking_id")
        if not tracking_id and not order_id:
            return {"error": "order_id or tracking_id is required"}
        if not tracking_id:
            tracking_id = await self.adapters.resolver.resolve_tracking_id(str(order_id))

        context = await self.adapters.logistics.build_logistics_context(str(tracking_id))
        response = {
            "service": self.service_name,
            "order_id": order_id,
            "tracking_id": tracking_id,
            "status": context.shipment.status if context else None,
            "events": [event.model_dump() for event in context.events] if context else [],
        }

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _order_status_instructions(self.service_name or "order status"),
                },
                {
                    "role": "user",
                    "content": response,
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return response


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for order status workflows."""
    adapters = getattr(agent, "adapters", build_order_status_adapters())

    async def get_order_status(payload: dict[str, Any]) -> dict[str, Any]:
        order_id = payload.get("order_id")
        tracking_id = payload.get("tracking_id")
        if not tracking_id and not order_id:
            return {"error": "order_id or tracking_id is required"}
        if not tracking_id:
            tracking_id = await adapters.resolver.resolve_tracking_id(str(order_id))
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        return {
            "order_id": order_id,
            "tracking_id": tracking_id,
            "status": context.shipment.status if context else None,
            "events": [event.model_dump() for event in context.events] if context else [],
        }

    async def get_order_events(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        events = await adapters.logistics.get_events(str(tracking_id))
        return {"tracking_id": tracking_id, "events": [event.model_dump() for event in events]}

    mcp.add_tool("/order/status", get_order_status)
    mcp.add_tool("/order/events", get_order_events)


def _order_status_instructions(service_name: str) -> str:
    return (
        f"You are the {service_name} agent. "
        "Be proactive about delivery risks and next steps. "
        "Summarize the latest shipment status and key events, "
        "and recommend actions if delays or exceptions appear. "
        "Always include a monitoring note: what to track next (e.g., carrier updates, "
        "exception codes, or ETA drift) and any anomalies to watch."
    )
