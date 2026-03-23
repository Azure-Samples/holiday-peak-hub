"""Truth HITL agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import HITLAdapters, build_hitl_adapters
from .review_manager import ReviewItem


class TruthHITLAgent(BaseRetailAgent):
    """Agent that manages the human-in-the-loop review queue for AI-proposed attributes."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_hitl_adapters()

    @property
    def adapters(self) -> HITLAdapters:
        return self._adapters

    @staticmethod
    def _to_ui_proposal(item: ReviewItem) -> dict[str, Any]:
        return {
            "id": item.attr_id,
            "field_name": item.field_name,
            "current_value": item.current_value,
            "proposed_value": str(item.proposed_value),
            "confidence": item.confidence,
            "source": item.source,
            "source_type": item.source_type,
            "evidence": [],
            "image_evidence": [],
            "source_assets": item.source_assets or [],
            "reasoning": item.reasoning,
            "proposed_at": item.proposed_at.isoformat(),
            "status": "pending",
        }

    @staticmethod
    def _to_ui_queue_item(item: ReviewItem) -> dict[str, Any]:
        return {
            "id": item.attr_id,
            "entity_id": item.entity_id,
            "product_title": item.product_title or item.entity_id,
            "category": item.category_label or "Unknown",
            "field_name": item.field_name,
            "current_value": item.current_value,
            "proposed_value": str(item.proposed_value),
            "confidence": item.confidence,
            "source": item.source,
            "proposed_at": item.proposed_at.isoformat(),
            "status": "pending",
        }

    @staticmethod
    def _to_ui_audit_event(event: Any) -> dict[str, Any]:
        return {
            "id": event.event_id,
            "entity_id": event.entity_id,
            "action": event.action,
            "field_name": None,
            "old_value": None if event.old_value is None else str(event.old_value),
            "new_value": None if event.new_value is None else str(event.new_value),
            "actor": event.reviewed_by or "system",
            "timestamp": event.timestamp.isoformat(),
            "reason": event.reason,
        }

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        action = request.get("action", "stats")

        if action == "stats":
            return {"stats": self._adapters.review_manager.stats()}

        if action == "queue":
            skip = int(request.get("skip", 0) or 0)
            limit = int(request.get("limit", 50) or 50)
            entity_id = request.get("entity_id")
            field_name = request.get("field_name")
            items = self._adapters.review_manager.list_pending(
                entity_id=entity_id,
                field_name=field_name,
                skip=skip,
                limit=limit,
            )
            return {
                "items": [self._to_ui_queue_item(item) for item in items],
                "count": len(items),
                "skip": skip,
                "limit": limit,
            }

        if action == "detail":
            entity_id = request.get("entity_id")
            if not entity_id:
                return {"error": "entity_id is required", "action": action}

            items = self._adapters.review_manager.get_by_entity(entity_id)
            product_title = items[0].product_title if items else entity_id
            category = items[0].category_label if items else "Unknown"
            return {
                "entity_id": entity_id,
                "product_title": product_title or entity_id,
                "category": category or "Unknown",
                "completeness_score": 0,
                "proposed_attributes": [self._to_ui_proposal(item) for item in items],
            }

        if action == "audit":
            entity_id = request.get("entity_id")
            events = self._adapters.review_manager.audit_log(entity_id=entity_id)
            return {
                "events": [self._to_ui_audit_event(event) for event in events],
                "count": len(events),
            }

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

    async def get_review_stats(_payload: dict[str, Any]) -> dict[str, Any]:
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
