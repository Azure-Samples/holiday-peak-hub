"""Unit tests for cached_handler utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.agents.memory.cached_handler import (
    CacheConfig,
    cache_write,
    inject_session_id,
    resolve_cache_key,
    try_cache_read,
)


@pytest.fixture()
def config():
    return CacheConfig(service="test-agent", entity_prefix="order")


@pytest.fixture()
def hot_memory():
    mem = AsyncMock()
    mem.get = AsyncMock(return_value=None)
    mem.set = AsyncMock()
    return mem


def test_resolve_cache_key_with_entity_id(config):
    request = {"entity_id": "sku-123", "tenant_id": "acme"}
    key = resolve_cache_key(request, config)
    assert key is not None
    assert "sku-123" in key
    assert "test-agent" in key


def test_resolve_cache_key_fallback_to_sku(config):
    request = {"sku": "WIDGET-01"}
    key = resolve_cache_key(request, config)
    assert key is not None
    assert "WIDGET-01" in key


def test_resolve_cache_key_returns_none_when_no_entity(config):
    request = {"random_field": "value"}
    key = resolve_cache_key(request, config)
    assert key is None


@pytest.mark.asyncio()
async def test_try_cache_read_returns_none_when_no_memory(config):
    result = await try_cache_read(None, "some-key")
    assert result is None


@pytest.mark.asyncio()
async def test_try_cache_read_returns_none_when_no_key(hot_memory):
    result = await try_cache_read(hot_memory, None)
    assert result is None


@pytest.mark.asyncio()
async def test_try_cache_read_returns_cached_value(hot_memory):
    hot_memory.get = AsyncMock(return_value={"cached": True})
    result = await try_cache_read(hot_memory, "v1|svc=test|key=order:123")
    assert result == {"cached": True}


@pytest.mark.asyncio()
async def test_cache_write_stores_value(hot_memory):
    await cache_write(hot_memory, "v1|key=order:123", {"result": "ok"}, ttl_seconds=600)
    hot_memory.set.assert_called_once_with(
        key="v1|key=order:123", value={"result": "ok"}, ttl_seconds=600
    )


@pytest.mark.asyncio()
async def test_cache_write_skips_when_no_memory():
    await cache_write(None, "key", {"result": "ok"})


@pytest.mark.asyncio()
async def test_cache_write_skips_when_no_key(hot_memory):
    await cache_write(hot_memory, None, {"result": "ok"})
    hot_memory.set.assert_not_called()


@pytest.mark.asyncio()
async def test_cache_write_skips_when_value_is_none(hot_memory):
    await cache_write(hot_memory, "key", None)
    hot_memory.set.assert_not_called()


def test_inject_session_id_preserves_existing(config):
    request = {"entity_id": "sku-1", "session_id": "existing-session"}
    result = inject_session_id(request, config)
    assert result["session_id"] == "existing-session"


def test_inject_session_id_creates_from_entity(config):
    request = {"entity_id": "sku-1"}
    result = inject_session_id(request, config)
    assert result["session_id"] == "test-agent:sku-1"
    assert result is not request  # immutable — new dict


def test_inject_session_id_uses_fallback_fields(config):
    request = {"sku": "WIDGET-01"}
    result = inject_session_id(request, config)
    assert result["session_id"] == "test-agent:WIDGET-01"


def test_inject_session_id_no_entity_no_change(config):
    request = {"random": "value"}
    result = inject_session_id(request, config)
    assert "session_id" not in result
