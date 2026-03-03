"""Sliding-window rate limiter for per-tenant endpoint protection."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Optional


class RateLimitExceededError(Exception):
    """Raised when a tenant exceeds their allowed request rate."""

    def __init__(self, tenant_id: str, limit: int, window_seconds: float) -> None:
        super().__init__(
            f"Rate limit exceeded for tenant '{tenant_id}': "
            f"max {limit} requests per {window_seconds}s window."
        )
        self.tenant_id = tenant_id
        self.limit = limit
        self.window_seconds = window_seconds


class RateLimiter:
    """Token-bucket / sliding-window rate limiter keyed by tenant ID.

    Uses a per-tenant :class:`~collections.deque` of request timestamps.
    Entries older than *window_seconds* are evicted on each check, keeping
    memory usage proportional to the burst size rather than total history.

    Args:
        limit: Maximum requests allowed within *window_seconds*.
        window_seconds: Length of the sliding time window in seconds.
    """

    def __init__(self, limit: int = 100, window_seconds: float = 60.0) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.limit = limit
        self.window_seconds = window_seconds
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, tenant_id: str) -> None:
        """Assert that *tenant_id* has not exceeded their rate limit.

        Raises:
            RateLimitExceededError: When the tenant has sent more than
                *limit* requests within the current window.
        """
        async with self._lock:
            now = time.monotonic()
            window = self._windows[tenant_id]
            cutoff = now - self.window_seconds

            # Evict timestamps outside the current window
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= self.limit:
                raise RateLimitExceededError(tenant_id, self.limit, self.window_seconds)

            window.append(now)

    async def remaining(self, tenant_id: str) -> int:
        """Return the number of remaining allowed requests for *tenant_id*.

        Args:
            tenant_id: The tenant to query.

        Returns:
            Non-negative integer representing remaining capacity.
        """
        async with self._lock:
            now = time.monotonic()
            window = self._windows[tenant_id]
            cutoff = now - self.window_seconds
            count = sum(1 for ts in window if ts >= cutoff)
            return max(0, self.limit - count)

    def reset(self, tenant_id: Optional[str] = None) -> None:
        """Reset rate-limit counters.

        Args:
            tenant_id: If provided, reset only this tenant's window.
                If ``None``, reset all tenants.
        """
        if tenant_id is not None:
            self._windows.pop(tenant_id, None)
        else:
            self._windows.clear()
