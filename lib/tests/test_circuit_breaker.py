"""Unit tests for the async circuit breaker."""

import asyncio

import pytest
from holiday_peak_lib.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    async def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=30.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_successful_call_returns_result(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=30.0)

        async def ok():
            return "value"

        result = await cb.call(ok)
        assert result == "value"
        assert cb.state == CircuitState.CLOSED

    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=30.0)

        async def failing():
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failing)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    async def test_open_circuit_raises_without_fallback(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=30.0)

        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing)

    async def test_open_circuit_calls_fallback(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=30.0)

        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        result = await cb.call(failing, fallback=lambda: "cached")
        assert result == "cached"

    async def test_async_fallback_is_awaited(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=30.0)

        async def failing():
            raise RuntimeError("boom")

        async def async_fallback():
            return "async-cached"

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        result = await cb.call(failing, fallback=async_fallback)
        assert result == "async-cached"

    async def test_half_open_transitions_to_closed_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)

        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.1)

        async def ok():
            return "recovered"

        result = await cb.call(ok)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    async def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)

        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        await asyncio.sleep(0.1)

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

    async def test_reset_restores_closed_state(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=30.0)

        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await cb.call(failing)

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=5, recovery_timeout=30.0)

        async def failing():
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failing)

        assert cb.failure_count == 3

        async def ok():
            return "ok"

        await cb.call(ok)
        assert cb.failure_count == 0
