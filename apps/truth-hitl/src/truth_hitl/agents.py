"""Truth HITL agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import HITLAdapters, build_hitl_adapters


class TruthHITLAgent(BaseRetailAgent):
    """Agent that manages the human-in-the-loop review queue for AI-proposed attributes."""

    def __init__(self, config: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_hitl_adapters()

    @property
    def adapters(self) -> HITLAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        action = request.get("action", "stats")

        if action == "stats":
            return {"stats": self._adapters.review_manager.stats()}

        entity_id = request.get("entity_id")
        if action == "list" and entity_id:
            items = self._adapters.review_manager.get_by_entity(entity_id)
            return {"entity_id": entity_id, "items": [i.model_dump() for i in items]}

        return {"error": "unsupported action or missing entity_id", "action": action}


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for the HITL review workflow."""
    adapters = getattr(agent, "adapters", build_hitl_adapters())

    async def get_review_queue(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = payload.get("entity_id")
        skip = int(payload.get("skip", 0))
        limit = int(payload.get("limit", 50))
        items = adapters.review_manager.list_pending(entity_id=entity_id, skip=skip, limit=limit)
        return {"items": [i.model_dump() for i in items], "count": len(items)}

    async def get_review_stats(payload: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        return {"stats": adapters.review_manager.stats()}

    async def get_audit_log(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = payload.get("entity_id")
        events = adapters.review_manager.audit_log(entity_id=entity_id)
        return {"events": [e.model_dump() for e in events], "count": len(events)}

    async def get_proposal(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = payload.get("entity_id")
        if not entity_id:
            return {"error": "entity_id is required"}

        attr_id = payload.get("attr_id")
        items = adapters.review_manager.get_by_entity(entity_id)
        if attr_id:
            items = [item for item in items if item.attr_id == attr_id]

        if not items:
            return {"entity_id": entity_id, "proposal": None}

        return {
            "entity_id": entity_id,
            "proposal": items[0].model_dump(),
        }

    mcp.add_tool("/hitl/queue", get_review_queue)
    mcp.add_tool("/hitl/stats", get_review_stats)
    mcp.add_tool("/hitl/audit", get_audit_log)
    mcp.add_tool("/review/get_proposal", get_proposal)
