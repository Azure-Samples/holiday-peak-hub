"""Tests for adapter base classes."""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from holiday_peak_lib.adapters.base import (
    BaseAdapter,
    AdapterError,
    BaseConnector,
)
from pydantic import BaseModel


class SampleModel(BaseModel):
    """Test Pydantic model."""
    id: str
    value: str


class SampleAdapter(BaseAdapter):
    """Concrete test adapter."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connected = False
        self.fetch_count = 0
        self.upsert_count = 0
        self.delete_count = 0

    async def _connect_impl(self, **kwargs):
        self.connected = True

    async def _fetch_impl(self, query):
        self.fetch_count += 1
        return [{"id": "1", "value": "test"}]

    async def _upsert_impl(self, payload):
        self.upsert_count += 1
        return payload

    async def _delete_impl(self, identifier):
        self.delete_count += 1
        return True


class FailingAdapter(BaseAdapter):
    """Adapter that always fails."""

    def __init__(self, fail_count=2, **kwargs):
        super().__init__(**kwargs)
        self.attempts = 0
        self.fail_count = fail_count

    async def _connect_impl(self, **kwargs):
        pass

    async def _fetch_impl(self, query):
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise ValueError("Simulated failure")
        return [{"id": "1"}]

    async def _upsert_impl(self, payload):
        raise NotImplementedError

    async def _delete_impl(self, identifier):
        raise NotImplementedError


class TestAdapterError:
    """Test AdapterError exception."""

    def test_adapter_error_creation(self):
        """Test creating an AdapterError."""
        error = AdapterError("test error")
        assert str(error) == "test error"

    def test_adapter_error_is_exception(self):
        """Test that AdapterError is an Exception."""
        error = AdapterError("test")
        assert isinstance(error, Exception)


class TestBaseAdapter:
    """Test BaseAdapter functionality."""

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test adapter connection."""
        adapter = SampleAdapter()
        await adapter.connect()
        assert adapter.connected is True

    @pytest.mark.asyncio
    async def test_fetch_returns_data(self):
        """Test fetching data."""
        adapter = SampleAdapter()
        result = await adapter.fetch({"query": "test"})
        assert len(list(result)) == 1
        assert adapter.fetch_count == 1

    @pytest.mark.asyncio
    async def test_fetch_uses_cache(self):
        """Test that fetch uses cache."""
        adapter = SampleAdapter(cache_ttl=10.0)
        # First fetch
        await adapter.fetch({"query": "test"})
        # Second fetch should use cache
        result2 = await adapter.fetch({"query": "test"})
        assert adapter.fetch_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_upsert_clears_cache(self):
        """Test that upsert clears cache."""
        adapter = SampleAdapter()
        # Fetch to populate cache
        await adapter.fetch({"query": "test"})
        # Upsert should clear cache
        await adapter.upsert({"id": "1", "value": "new"})
        # Next fetch should not use cache
        await adapter.fetch({"query": "test"})
        assert adapter.fetch_count == 2

    @pytest.mark.asyncio
    async def test_delete_clears_cache(self):
        """Test that delete clears cache."""
        adapter = SampleAdapter()
        await adapter.fetch({"query": "test"})
        await adapter.delete("1")
        await adapter.fetch({"query": "test"})
        assert adapter.fetch_count == 2
        assert adapter.delete_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism on failure."""
        adapter = FailingAdapter(
            fail_count=2,
            retries=3,
            base_delay=0.01,
            timeout=1.0
        )
        result = await adapter.fetch({"query": "test"})
        assert adapter.attempts == 3  # Failed twice, succeeded third time

    @pytest.mark.asyncio
    async def test_failure_raises_after_retries(self):
        """Test that failure raises after exhausting retries."""
        adapter = FailingAdapter(
            fail_count=10,
            retries=2,
            base_delay=0.01,
            timeout=1.0
        )
        with pytest.raises(AdapterError, match="Operation failed after retries"):
            await adapter.fetch({"query": "test"})

    @pytest.mark.asyncio
    async def test_timeout_mechanism(self):
        """Test timeout mechanism."""
        class SlowAdapter(BaseAdapter):
            async def _connect_impl(self, **kwargs):
                pass

            async def _fetch_impl(self, query):
                await asyncio.sleep(10)  # Sleep longer than timeout
                return []

            async def _upsert_impl(self, payload):
                pass

            async def _delete_impl(self, identifier):
                return True

        adapter = SlowAdapter(timeout=0.1, retries=0)
        with pytest.raises(AdapterError):
            await adapter.fetch({"query": "test"})

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after threshold."""
        adapter = FailingAdapter(
            fail_count=10,
            circuit_breaker_threshold=3,
            retries=0,
            timeout=1.0,
            base_delay=0.01
        )
        
        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(AdapterError):
                await adapter.fetch({"query": "test"})
        
        # Next call should fail immediately due to open circuit
        with pytest.raises(AdapterError, match="Circuit breaker open"):
            await adapter.fetch({"query": "test"})

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        adapter = SampleAdapter(max_calls=2, per_seconds=1.0)
        
        start = asyncio.get_event_loop().time()
        # First two calls should be immediate
        await adapter.fetch({"query": "1"})
        await adapter.fetch({"query": "2"})
        # Third call should be delayed
        await adapter.fetch({"query": "3"})
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed >= 0.9  # Should have waited ~1 second

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        adapter = SampleAdapter()
        key1 = adapter._cache_key({"a": 1, "b": 2})
        key2 = adapter._cache_key({"b": 2, "a": 1})
        key3 = adapter._cache_key({"a": 1, "c": 3})
        
        assert key1 == key2  # Order shouldn't matter
        assert key1 != key3  # Different content

    @pytest.mark.asyncio
    async def test_adapter_configuration(self):
        """Test adapter with custom configuration."""
        adapter = SampleAdapter(
            max_calls=5,
            per_seconds=2.0,
            cache_ttl=60.0,
            cache_size=512,
            retries=5,
            base_delay=0.2,
            max_delay=2.0,
            timeout=10.0,
            circuit_breaker_threshold=10,
            circuit_reset_seconds=60.0
        )
        assert adapter._max_calls == 5
        assert adapter._per_seconds == 2.0
        assert adapter._cache_ttl == 60.0
        assert adapter._retries == 5


class TestBaseConnector:
    """Test BaseConnector functionality."""

    @pytest.mark.asyncio
    async def test_fetch_first(self):
        """Test _fetch_first functionality."""
        mock_adapter = SampleAdapter()
        connector = BaseConnector(mock_adapter, map_concurrency=2)
        
        result = await connector._fetch_first(query="test")
        
        assert result is not None
        assert result["id"] == "1"

    @pytest.mark.asyncio
    async def test_fetch_many(self):
        """Test _fetch_many functionality."""
        mock_adapter = SampleAdapter()
        connector = BaseConnector(mock_adapter, map_concurrency=2)
        
        results = await connector._fetch_many(query="test")
        
        assert len(results) == 1
        assert results[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_map_single(self):
        """Test _map_single functionality."""
        connector = BaseConnector(map_concurrency=2)
        
        result = await connector._map_single(
            SampleModel,
            {"id": "1", "value": "test"}
        )
        
        assert isinstance(result, SampleModel)
        assert result.id == "1"

    @pytest.mark.asyncio
    async def test_map_single_none(self):
        """Test _map_single with None payload."""
        connector = BaseConnector(map_concurrency=2)
        
        result = await connector._map_single(SampleModel, None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_map_many(self):
        """Test _map_many functionality."""
        connector = BaseConnector(map_concurrency=2)
        
        payloads = [
            {"id": "1", "value": "test1"},
            {"id": "2", "value": "test2"}
        ]
        
        results = await connector._map_many(SampleModel, payloads)
        
        assert len(results) == 2
        assert all(isinstance(r, SampleModel) for r in results)
