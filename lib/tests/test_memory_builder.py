"""Tests for memory builder and cascading memory client behavior."""

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.agents.memory.builder import MemoryBuilder, MemoryClient


def test_memory_builder_requires_at_least_one_tier() -> None:
    """Builder should reject creation when no memory tiers are configured."""
    with pytest.raises(ValueError, match="At least one memory tier must be configured"):
        MemoryBuilder().build()


def test_memory_builder_builds_client_with_rules() -> None:
    """Builder should construct a memory client preserving configured rules."""
    hot = AsyncMock()

    client = (
        MemoryBuilder()
        .with_hot(hot)
        .with_rules(read_fallback=False, hot_ttl_seconds=120, write_through=False)
        .build()
    )

    assert isinstance(client, MemoryClient)
    assert client.hot is hot
    assert client.rules.read_fallback is False
    assert client.rules.hot_ttl_seconds == 120
    assert client.rules.write_through is False


@pytest.mark.asyncio
async def test_memory_client_reads_from_warm_and_promotes_to_hot() -> None:
    """Warm read should return value and promote to hot memory when configured."""
    hot = AsyncMock()
    hot.get = AsyncMock(return_value=None)
    warm = AsyncMock()
    warm.read = AsyncMock(return_value={"id": "k1", "value": {"score": 9}})

    client = MemoryBuilder().with_hot(hot).with_warm(warm).build()
    value = await client.get("k1")

    assert value == {"score": 9}
    hot.set.assert_awaited_once_with("k1", {"score": 9}, ttl_seconds=300)


@pytest.mark.asyncio
async def test_memory_client_reads_from_cold_and_promotes_to_hot_and_warm() -> None:
    """Cold read should decode bytes and promote to hot and warm tiers."""
    hot = AsyncMock()
    hot.get = AsyncMock(return_value=None)
    warm = AsyncMock()
    warm.read = AsyncMock(return_value=None)
    cold = AsyncMock()
    cold.download_text = AsyncMock(return_value=b"cold-value")

    client = (
        MemoryBuilder()
        .with_hot(hot)
        .with_warm(warm)
        .with_cold(cold)
        .with_rules(warm_ttl_seconds=1800)
        .build()
    )

    value = await client.get("k2")

    assert value == "cold-value"
    hot.set.assert_awaited_once_with("k2", "cold-value", ttl_seconds=300)
    warm.upsert.assert_awaited_once_with(
        {"id": "k2", "pk": "k2", "value": "cold-value", "ttl": 1800}
    )


@pytest.mark.asyncio
async def test_memory_client_set_writes_through_and_to_cold_when_enabled() -> None:
    """Set should write to configured tiers according to cascading rules."""
    hot = AsyncMock()
    warm = AsyncMock()
    cold = AsyncMock()

    client = (
        MemoryBuilder()
        .with_hot(hot)
        .with_warm(warm)
        .with_cold(cold)
        .with_rules(write_through=True, write_cold=True, warm_ttl_seconds=600)
        .build()
    )

    await client.set("k3", {"status": "ok"})

    hot.set.assert_awaited_once_with("k3", {"status": "ok"}, ttl_seconds=300)
    warm.upsert.assert_awaited_once_with(
        {"id": "k3", "pk": "k3", "value": {"status": "ok"}, "ttl": 600}
    )
    cold.upload_text.assert_awaited_once_with("k3", '{"status": "ok"}')


@pytest.mark.asyncio
async def test_memory_client_parallel_hot_warm_read_hot_wins() -> None:
    """When both hot and warm return values, hot value takes precedence."""
    hot = AsyncMock()
    hot.get = AsyncMock(return_value="hot-data")
    warm = AsyncMock()
    warm.read = AsyncMock(return_value={"id": "k", "value": "warm-data"})

    client = MemoryBuilder().with_hot(hot).with_warm(warm).build()
    value = await client.get("k")

    assert value == "hot-data"
    # Hot hit means no promotion needed
    hot.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_memory_client_parallel_writes() -> None:
    """Set should dispatch all tier writes concurrently."""
    hot = AsyncMock()
    warm = AsyncMock()
    cold = AsyncMock()

    client = (
        MemoryBuilder()
        .with_hot(hot)
        .with_warm(warm)
        .with_cold(cold)
        .with_rules(write_through=True, write_cold=True)
        .build()
    )
    await client.set("pk", "val")

    hot.set.assert_awaited_once()
    warm.upsert.assert_awaited_once()
    cold.upload_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_client_cold_parallel_promotion() -> None:
    """Cold read should promote to hot and warm in parallel."""
    hot = AsyncMock()
    hot.get = AsyncMock(return_value=None)
    warm = AsyncMock()
    warm.read = AsyncMock(return_value=None)
    cold = AsyncMock()
    cold.download_text = AsyncMock(return_value="archive")

    client = MemoryBuilder().with_hot(hot).with_warm(warm).with_cold(cold).build()
    value = await client.get("ck")

    assert value == "archive"
    hot.set.assert_awaited_once()
    warm.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_client_single_hot_fast_path() -> None:
    """When only hot is configured, use single-tier fast path."""
    hot = AsyncMock()
    hot.get = AsyncMock(return_value="cached")

    client = MemoryBuilder().with_hot(hot).build()
    value = await client.get("solo")

    assert value == "cached"


from holiday_peak_lib.agents.base_agent import AgentDependencies, BaseRetailAgent


class _StubAgent(BaseRetailAgent):
    async def handle(self, request: dict) -> dict:
        return {}


@pytest.mark.asyncio
async def test_base_agent_memory_tool_definitions() -> None:
    """Memory tools should be generated when memory_client is set."""
    memory = AsyncMock()
    memory.get = AsyncMock(return_value="recalled")
    memory.set = AsyncMock()

    deps = AgentDependencies(memory_client=memory)
    agent = _StubAgent(config=deps)
    tools = agent.memory_tool_definitions()

    assert "memory_read" in tools
    assert "memory_write" in tools

    result = await tools["memory_read"](key="k")
    assert result == "recalled"

    result = await tools["memory_write"](key="k", value="v")
    assert result == "stored"
    memory.set.assert_awaited_once_with("k", "v")


@pytest.mark.asyncio
async def test_base_agent_gather_adapters() -> None:
    """gather_adapters should execute coroutines concurrently."""

    async def coro_a():
        return "a"

    async def coro_b():
        return "b"

    deps = AgentDependencies()
    agent = _StubAgent(config=deps)
    a, b = await agent.gather_adapters(coro_a(), coro_b())

    assert a == "a"
    assert b == "b"
