"""Tests for the default service agent implementation."""

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.service_agent import ServiceAgent


@pytest.mark.asyncio
async def test_service_agent_echoes_payload_with_service_name() -> None:
    """ServiceAgent should include service metadata and the original payload."""
    agent = ServiceAgent(config=AgentDependencies(service_name="orders"))

    payload = {"query": "status", "order_id": "O-100"}
    result = await agent.handle(payload)

    assert result == {"service": "orders", "received": payload}


@pytest.mark.asyncio
async def test_service_agent_uses_empty_service_name_when_unset() -> None:
    """ServiceAgent should default service name to empty string when not configured."""
    agent = ServiceAgent(config=AgentDependencies())

    payload = {"query": "ping"}
    result = await agent.handle(payload)

    assert result == {"service": "", "received": payload}
