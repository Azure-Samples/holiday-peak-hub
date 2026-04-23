"""FastAPI router exposing the agent's async communication contract.

Returns a factory function that creates a router with GET /async/contract.
The app_factory auto-registers this when an AgentAsyncContract is provided.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from holiday_peak_lib.messaging.async_contract import AgentAsyncContract


def build_contract_router(contract: AgentAsyncContract) -> APIRouter:
    """Create a FastAPI router that serves the agent's async contract.

    Parameters
    ----------
    contract:
        The ``AgentAsyncContract`` to expose at ``GET /async/contract``.

    Returns
    -------
    APIRouter
        A router with a single ``GET /async/contract`` endpoint.
    """
    router = APIRouter(tags=["messaging"])

    @router.get("/async/contract")
    async def get_async_contract() -> dict[str, Any]:
        return contract.model_dump()

    return router
