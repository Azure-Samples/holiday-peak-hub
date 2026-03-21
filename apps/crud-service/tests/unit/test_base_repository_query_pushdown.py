"""Unit tests for BaseRepository SQL pushdown query path."""

import pytest
from crud_service.repositories import ProductRepository


class _FakeAcquire:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self):
        self.calls: list[tuple[str, tuple, float | None]] = []

    async def fetch(self, sql, *args, timeout=None):
        self.calls.append((sql, args, timeout))
        return [{"data": {"id": "prod-1", "name": "Widget", "category_id": "cat-1"}}]


class _FakePool:
    def __init__(self, connection):
        self._connection = connection

    def acquire(self):
        return _FakeAcquire(self._connection)


async def _noop(*_args, **_kwargs):
    return None


@pytest.mark.asyncio
async def test_query_pushes_down_limit_without_full_scan(monkeypatch):
    """Default list query should compile to SQL with LIMIT pushdown."""
    connection = _FakeConnection()
    pool = _FakePool(connection)
    repo = ProductRepository()

    monkeypatch.setattr(repo, "_ensure_table", _noop)

    async def _fake_get_pool():
        return pool

    monkeypatch.setattr(repo, "_get_pool", _fake_get_pool)

    result = await repo.query(
        query="SELECT * FROM c OFFSET 0 LIMIT @limit",
        parameters=[{"name": "@limit", "value": 20}],
    )

    assert len(result) == 1
    sql, args, timeout = connection.calls[0]
    assert sql.startswith("SELECT data FROM products")
    assert "LIMIT $" in sql
    assert "SELECT data FROM products WHERE" not in sql
    assert args[-1] == 20
    assert timeout is not None


@pytest.mark.asyncio
async def test_query_pushes_down_contains_filter(monkeypatch):
    """Name search query should be translated to SQL LIKE predicate."""
    connection = _FakeConnection()
    pool = _FakePool(connection)
    repo = ProductRepository()

    monkeypatch.setattr(repo, "_ensure_table", _noop)

    async def _fake_get_pool():
        return pool

    monkeypatch.setattr(repo, "_get_pool", _fake_get_pool)

    await repo.query(
        query="SELECT * FROM c WHERE CONTAINS(LOWER(c.name), LOWER(@term)) OFFSET 0 LIMIT @limit",
        parameters=[
            {"name": "@term", "value": "widget"},
            {"name": "@limit", "value": 5},
        ],
    )

    sql, args, _timeout = connection.calls[0]
    assert "LOWER(data->>'name') LIKE LOWER(" in sql
    assert "%widget%" in args
    assert 5 in args
