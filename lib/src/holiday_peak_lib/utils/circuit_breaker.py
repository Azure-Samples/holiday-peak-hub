"""Async circuit breaker implementation for external service calls."""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""

    def __init__(self, name: str, recovery_timeout: float) -> None:
        super().__init__(f"Circuit '{name}' is OPEN. Retry after {recovery_timeout:.1f}s.")
        self.name = name
        self.recovery_timeout = recovery_timeout


class CircuitBreaker:
    """Async circuit breaker with configurable thresholds and recovery.

    States:
    - CLOSED: Normal operation. Failures increment a counter.
    - OPEN: All calls are rejected immediately; a fallback is returned.
    - HALF_OPEN: A single probe call is allowed to test recovery.

    Args:
        name: Human-readable name used in logs and errors.
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait before attempting recovery.
        half_open_max_calls: Maximum concurrent probe calls in HALF_OPEN state.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def _transition(self, new_state: CircuitState) -> None:
        self._state = new_state
        logger.info(
            "circuit_breaker name=%s state=%s failures=%d",
            self.name,
            new_state.value,
            self._failure_count,
        )

    async def _check_recovery(self) -> None:
        """Transition from OPEN to HALF_OPEN if the recovery timeout has elapsed."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time is not None
            and (time.monotonic() - self._last_failure_time) >= self.recovery_timeout
        ):
            self._failure_count = 0
            self._half_open_calls = 0
            await self._transition(CircuitState.HALF_OPEN)

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        fallback: Optional[Callable[[], Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute *func* through the circuit breaker.

        Args:
            func: Async callable to protect.
            *args: Positional arguments forwarded to *func*.
            fallback: Optional zero-argument callable invoked when the circuit
                is open.  If ``None`` a :class:`CircuitBreakerOpenError` is
                raised instead.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The result of *func*, or the result of *fallback* if the circuit
            is open.

        Raises:
            CircuitBreakerOpenError: When the circuit is open and no fallback
                is provided.
        """
        async with self._lock:
            await self._check_recovery()

            if self._state == CircuitState.OPEN:
                remaining = self.recovery_timeout - (
                    time.monotonic() - (self._last_failure_time or time.monotonic())
                )
                if fallback is not None:
                    return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
                raise CircuitBreakerOpenError(self.name, max(remaining, 0.0))

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    if fallback is not None:
                        return (
                            await fallback()
                            if asyncio.iscoroutinefunction(fallback)
                            else fallback()
                        )
                    raise CircuitBreakerOpenError(self.name, 0.0)
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._failure_count = 0
                self._half_open_calls = 0
                if self._state != CircuitState.CLOSED:
                    await self._transition(CircuitState.CLOSED)
            return result
        except Exception:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._state == CircuitState.HALF_OPEN or (
                    self._state == CircuitState.CLOSED
                    and self._failure_count >= self.failure_threshold
                ):
                    await self._transition(CircuitState.OPEN)
            raise

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
