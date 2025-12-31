from holiday_peak_lib.adapters.inventory_adapter import InventoryAdapter
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
import pytest


class DemoAgent(BaseRetailAgent):
    async def handle(self, request):
        return {"ok": True, "request": request}


def test_builder_creates_agent():
    builder = AgentBuilder()
    router = RoutingStrategy()
    agent = (
        builder.with_agent(DemoAgent)
        .with_router(router)
        .with_memory(HotMemory("redis://localhost:6379"), None, None)
        .build()
    )
    assert isinstance(agent, DemoAgent)


@pytest.mark.asyncio
async def test_adapter_stub_fetch():
    adapter = InventoryAdapter()
    results = await adapter.fetch({"sku": "123"})
    assert results
