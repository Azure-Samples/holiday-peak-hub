"""Unit tests for BaseRepository.check_pool_health recovery semantics (#911)."""

import pytest
from crud_service.repositories.base import BaseRepository


class _FakeAcquire:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    async def fetchval(self, _sql, *_args):
        return 1


class _FakePool:
    def __init__(self):
        self._connection = _FakeConnection()

    def acquire(self):
        return _FakeAcquire(self._connection)


@pytest.fixture(autouse=True)
def _reset_pool_state():
    """Reset BaseRepository class state between tests so they don't leak."""
    original_pool = BaseRepository._pool
    original_error = BaseRepository._pool_init_error
    BaseRepository._pool = None
    BaseRepository._pool_init_error = None
    yield
    BaseRepository._pool = original_pool
    BaseRepository._pool_init_error = original_error


@pytest.mark.asyncio
async def test_check_pool_health_returns_healthy_when_pool_already_initialized():
    """Happy path: pool is up, SELECT 1 succeeds."""
    BaseRepository._pool = _FakePool()
    BaseRepository._pool_init_error = None

    status, detail = await BaseRepository.check_pool_health()

    assert status == "healthy"
    assert detail == "query ok"


@pytest.mark.asyncio
async def test_check_pool_health_clears_stale_init_error_on_successful_retry(monkeypatch):
    """Regression for #911: a transient startup error must not stick.

    If ``initialize_pool`` failed earlier (cached in ``_pool_init_error``) but a
    later retry succeeds, the readiness check must report healthy and clear the
    cached error so subsequent callers see a clean state.
    """
    BaseRepository._pool = None
    BaseRepository._pool_init_error = "TimeoutError: "

    async def _fake_initialize_pool():
        BaseRepository._pool = _FakePool()
        BaseRepository._pool_init_error = None

    monkeypatch.setattr(BaseRepository, "initialize_pool", _fake_initialize_pool)

    status, detail = await BaseRepository.check_pool_health()

    assert status == "healthy"
    assert detail == "query ok"
    assert BaseRepository._pool_init_error is None


@pytest.mark.asyncio
async def test_check_pool_health_reports_latest_error_when_retry_still_fails(monkeypatch):
    """When the retry itself raises, the latest exception is reported."""
    BaseRepository._pool = None
    BaseRepository._pool_init_error = "TimeoutError: "

    async def _failing_initialize_pool():
        raise ConnectionError("postgres unreachable")

    monkeypatch.setattr(BaseRepository, "initialize_pool", _failing_initialize_pool)

    status, detail = await BaseRepository.check_pool_health()

    assert status == "unhealthy"
    assert "ConnectionError" in detail
    assert "postgres unreachable" in detail
    assert BaseRepository._pool_init_error == detail


@pytest.mark.asyncio
async def test_check_pool_health_does_not_short_circuit_on_cached_error(monkeypatch):
    """Regression for #911: a cached error must not bypass the retry."""
    BaseRepository._pool = None
    BaseRepository._pool_init_error = "TimeoutError: "

    init_attempts: list[int] = []

    async def _counting_initialize_pool():
        init_attempts.append(1)
        BaseRepository._pool = _FakePool()
        BaseRepository._pool_init_error = None

    monkeypatch.setattr(BaseRepository, "initialize_pool", _counting_initialize_pool)

    await BaseRepository.check_pool_health()

    assert init_attempts == [1], "initialize_pool must be retried even when an error is cached"
