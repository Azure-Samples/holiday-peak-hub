"""CRM segmentation and personalization agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    register_crud_tools,
)

from .adapters import SegmentationAdapters, build_segmentation_adapters


class SegmentationPersonalizationAgent(BaseRetailAgent):
    """Agent that segments contacts and recommends personalization."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_segmentation_adapters()

    @property
    def adapters(self) -> SegmentationAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        contact_id = request.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}

        interaction_limit = int(request.get("interaction_limit", 20))
        context = await self.adapters.crm.build_contact_context(
            contact_id, interaction_limit=interaction_limit
        )
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}

        segmentation = await self.adapters.segmenter.build_segment(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _segmentation_instructions()},
                {
                    "role": "user",
                    "content": {
                        "query": request.get("query", ""),
                        "contact_id": contact_id,
                        "crm_context": context.model_dump(),
                        "segmentation": segmentation,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "contact_id": contact_id,
            "crm_context": context.model_dump(),
            "segmentation": segmentation,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for CRM segmentation workflows."""
    adapters = get_agent_adapters(agent, build_segmentation_adapters)

    async def get_contact_context(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        limit = int(payload.get("interaction_limit", 20))
        context = await adapters.crm.build_contact_context(contact_id, interaction_limit=limit)
        return {"crm_context": context.model_dump() if context else None}

    async def get_segment(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        context = await adapters.crm.build_contact_context(contact_id)
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}
        segmentation = await adapters.segmenter.build_segment(context)
        return {"segmentation": segmentation}

    async def get_personalization(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        context = await adapters.crm.build_contact_context(contact_id)
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}
        segmentation = await adapters.segmenter.build_segment(context)
        return {"personalization": segmentation.get("personalization", {})}

    mcp.add_tool("/crm/segmentation/context", get_contact_context)
    mcp.add_tool("/crm/segmentation/segment", get_segment)
    mcp.add_tool("/crm/segmentation/personalization", get_personalization)
    register_crud_tools(mcp)


def _segmentation_instructions() -> str:
    return load_prompt_instructions(__file__, "crm-segmentation-personalization")
