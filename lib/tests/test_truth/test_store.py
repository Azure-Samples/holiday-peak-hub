"""Tests for TruthStoreAdapter (Issue #91)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from holiday_peak_lib.truth.store import TruthStoreAdapter


def make_adapter(container_mock=None):
    """Return a connected TruthStoreAdapter backed by a mock Cosmos container."""
    client = MagicMock()
    db_mock = MagicMock()
    container = container_mock or AsyncMock()
    client.get_database_client.return_value = db_mock
    db_mock.get_container_client.return_value = container

    adapter = TruthStoreAdapter(
        cosmos_client=client,
        database_name="test-db",
        container_name="products",
        retries=0,
        timeout=5.0,
        cache_ttl=0,
    )
    return adapter, container


@pytest.mark.asyncio
async def test_connect_resolves_container():
    adapter, container = make_adapter()
    await adapter.connect()
    assert adapter._container_proxy is container


@pytest.mark.asyncio
async def test_fetch_point_read():
    adapter, container = make_adapter()
    await adapter.connect()
    container.read_item = AsyncMock(return_value={"id": "1", "name": "T-Shirt"})

    results = list(await adapter.fetch({"id": "1", "partition_key": "apparel"}))
    assert results[0]["name"] == "T-Shirt"
    container.read_item.assert_called_once_with(item="1", partition_key="apparel")


@pytest.mark.asyncio
async def test_fetch_point_read_not_found():
    adapter, container = make_adapter()
    await adapter.connect()
    container.read_item = AsyncMock(side_effect=Exception("404"))

    results = list(await adapter.fetch({"id": "missing", "partition_key": "apparel"}))
    assert results == []


@pytest.mark.asyncio
async def test_fetch_query():
    adapter, container = make_adapter()
    await adapter.connect()

    async def _iter(*args, **kwargs):
        yield {"id": "2", "name": "Polo"}

    container.query_items = MagicMock(return_value=_iter())

    results = list(await adapter.fetch({"category_id": "apparel"}))
    assert results[0]["name"] == "Polo"


@pytest.mark.asyncio
async def test_upsert_document():
    adapter, container = make_adapter()
    await adapter.connect()
    doc = {"id": "3", "name": "Jeans", "categoryId": "apparel"}
    container.upsert_item = AsyncMock(return_value=doc)

    result = await adapter.upsert(doc)
    assert result["name"] == "Jeans"
    container.upsert_item.assert_called_once_with(body=doc)


@pytest.mark.asyncio
async def test_delete_document():
    adapter, container = make_adapter()
    await adapter.connect()
    container.delete_item = AsyncMock(return_value=None)

    result = await adapter.delete("item-id:apparel")
    assert result is True
    container.delete_item.assert_called_once_with(item="item-id", partition_key="apparel")


@pytest.mark.asyncio
async def test_get_by_id_helper():
    adapter, container = make_adapter()
    await adapter.connect()
    container.read_item = AsyncMock(return_value={"id": "5", "name": "Hoodie"})

    result = await adapter.get_by_id("5", "apparel")
    assert result["name"] == "Hoodie"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing():
    adapter, container = make_adapter()
    await adapter.connect()
    container.read_item = AsyncMock(side_effect=Exception("not found"))

    result = await adapter.get_by_id("missing", "apparel")
    assert result is None


@pytest.mark.asyncio
async def test_assert_connected_raises():
    client = MagicMock()
    adapter = TruthStoreAdapter(
        cosmos_client=client,
        database_name="db",
        container_name="products",
        retries=0,
    )
    with pytest.raises(RuntimeError, match="not connected"):
        await adapter._fetch_impl({})
