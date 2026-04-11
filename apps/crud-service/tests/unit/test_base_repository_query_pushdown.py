"""Unit tests for BaseRepository SQL pushdown query path."""

import pytest
from crud_service.repositories import BaseRepository, ProductRepository


class _FakeAcquire:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, *, table_exists: bool = True):
        self.calls: list[tuple[str, tuple, float | None]] = []
        self.fetchval_calls: list[tuple[str, tuple[object, ...]]] = []
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self._table_exists = table_exists

    async def fetch(self, sql, *args, timeout=None):
        self.calls.append((sql, args, timeout))
        return [{"data": {"id": "prod-1", "name": "Widget", "category_id": "cat-1"}}]

    async def fetchval(self, sql, *args):
        self.fetchval_calls.append((sql, args))
        return self._table_exists

    async def execute(self, sql, *args):
        self.execute_calls.append((sql, args))
        return "OK"


class _FakePool:
    def __init__(self, connection):
        self._connection = connection

    def acquire(self):
        return _FakeAcquire(self._connection)


async def _noop(*_args, **_kwargs):
    return None


@pytest.fixture(autouse=True)
def _reset_initialized_tables(monkeypatch):
    monkeypatch.setattr(BaseRepository, "_initialized_tables", set())


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


@pytest.mark.asyncio
async def test_ensure_table_skips_bootstrap_ddl_for_existing_table(monkeypatch):
    """Existing tables should avoid ownership-dependent bootstrap DDL."""
    connection = _FakeConnection(table_exists=True)
    pool = _FakePool(connection)
    repo = ProductRepository()

    async def _fake_get_pool():
        return pool

    monkeypatch.setattr(repo, "_get_pool", _fake_get_pool)

    await repo._ensure_table()
    await repo._ensure_table()

    assert connection.fetchval_calls == [("SELECT to_regclass($1) IS NOT NULL", ("products",))]
    assert connection.execute_calls == []
    assert "products" in BaseRepository._initialized_tables


@pytest.mark.asyncio
async def test_ensure_table_bootstraps_missing_table_once(monkeypatch):
    """Missing tables should still be created and indexed during bootstrap."""
    connection = _FakeConnection(table_exists=False)
    pool = _FakePool(connection)
    repo = ProductRepository()

    async def _fake_get_pool():
        return pool

    monkeypatch.setattr(repo, "_get_pool", _fake_get_pool)

    await repo._ensure_table()
    await repo._ensure_table()

    assert connection.fetchval_calls == [("SELECT to_regclass($1) IS NOT NULL", ("products",))]
    assert len(connection.execute_calls) == 3
    assert "CREATE TABLE IF NOT EXISTS products" in connection.execute_calls[0][0]
    assert (
        "CREATE INDEX IF NOT EXISTS idx_products_partition_key ON products(partition_key)"
        in connection.execute_calls[1][0]
    )
    assert (
        "CREATE INDEX IF NOT EXISTS idx_products_data_gin ON products USING GIN (data)"
        in connection.execute_calls[2][0]
    )
    assert "products" in BaseRepository._initialized_tables
