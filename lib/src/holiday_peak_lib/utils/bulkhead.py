"""Bulkhead pattern: isolate concurrent workloads with per-key semaphores."""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BulkheadFullError(Exception):
    """Raised when a bulkhead has no available capacity."""

    def __init__(self, name: str, concurrency_limit: int) -> None:
        super().__init__(
            f"Bulkhead '{name}' is full (limit={concurrency_limit}). "
            "Request rejected to protect downstream resources."
        )
        self.name = name
        self.concurrency_limit = concurrency_limit


class Bulkhead:
    """Async bulkhead that limits concurrent executions for a named workload.

    Use one :class:`Bulkhead` instance per isolated pipeline stage (e.g.
    ``enrichment``, ``export``, ``ingestion``).  When the semaphore is
    exhausted, incoming calls are either queued (``queue_timeout > 0``) or
    rejected immediately (``queue_timeout=0``).

    Args:
        name: Human-readable label used in logs and errors.
        concurrency_limit: Maximum number of simultaneous calls allowed.
        queue_timeout: Seconds to wait for a slot before raising
            :class:`BulkheadFullError`.  ``0`` means fail-fast; ``None``
            means wait indefinitely.
    """

    def __init__(
        self,
        name: str,
        concurrency_limit: int = 10,
        queue_timeout: Optional[float] = 0.0,
    ) -> None:
        if concurrency_limit < 1:
            raise ValueError("concurrency_limit must be >= 1")
        self.name = name
        self.concurrency_limit = concurrency_limit
        self.queue_timeout = queue_timeout
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        self._active = 0

    @property
    def active_calls(self) -> int:
        """Number of calls currently being executed."""
        return self._active

    @property
    def available_slots(self) -> int:
        """Remaining capacity."""
        return self.concurrency_limit - self._active

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute *func* inside the bulkhead.

        Args:
            func: Async callable to execute.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            BulkheadFullError: When no slot is available within
                *queue_timeout* seconds.
        """
        try:
            if self.queue_timeout == 0.0:
                if self._semaphore.locked():
                    raise BulkheadFullError(self.name, self.concurrency_limit)
                # semaphore.acquire() does not yield when capacity is available
                await self._semaphore.acquire()
            elif self.queue_timeout is None:
                await self._semaphore.acquire()
            else:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=self.queue_timeout)
        except BulkheadFullError:
            raise
        except asyncio.TimeoutError as exc:
            logger.warning(
                "bulkhead name=%s limit=%d active=%d status=rejected",
                self.name,
                self.concurrency_limit,
                self._active,
            )
            raise BulkheadFullError(self.name, self.concurrency_limit) from exc

        self._active += 1
        logger.debug(
            "bulkhead name=%s limit=%d active=%d status=acquired",
            self.name,
            self.concurrency_limit,
            self._active,
        )
        try:
            return await func(*args, **kwargs)
        finally:
            self._semaphore.release()
            self._active -= 1
            logger.debug(
                "bulkhead name=%s limit=%d active=%d status=released",
                self.name,
                self.concurrency_limit,
                self._active,
            )
