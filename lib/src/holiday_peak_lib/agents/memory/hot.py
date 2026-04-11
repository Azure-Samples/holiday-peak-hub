"""Hot memory layer using Redis."""

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

import redis.asyncio as redis
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation
from redis import exceptions as redis_exceptions

logger = configure_logging()
T = TypeVar("T")
_REDIS_FAIL_OPEN_EXCEPTIONS = (
    redis_exceptions.AuthenticationError,
    redis_exceptions.ConnectionError,
    redis_exceptions.TimeoutError,
    OSError,
)


class HotMemory:
    """Redis-backed hot memory for short-lived context."""

    def __init__(
        self,
        url: str,
        *,
        max_connections: int | None = None,
        socket_timeout: float | None = None,
        socket_connect_timeout: float | None = None,
        health_check_interval: int | None = None,
        retry_on_timeout: bool | None = None,
    ) -> None:
        self.url = url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.health_check_interval = health_check_interval
        self.retry_on_timeout = retry_on_timeout
        self.client: redis.Redis | None = None
        self._connect_lock = asyncio.Lock()

    def _log_degraded_operation(self, operation: str, key: str, exc: Exception) -> None:
        self.client = None
        logger.warning(
            "hot_memory.%s degraded to fail-open mode; key=%s url=%s error_type=%s error=%s",
            operation,
            key,
            self.url,
            type(exc).__name__,
            exc,
        )

    # Decorator-style fail-open wrapper keeps optional cache faults from reaching agents.
    async def _run_fail_open(
        self,
        *,
        operation: str,
        key: str,
        fallback: T,
        metadata: dict[str, Any] | None,
        func: Callable[[redis.Redis], Awaitable[T]],
    ) -> T:
        if self.client is None:
            try:
                await self.connect()
            except _REDIS_FAIL_OPEN_EXCEPTIONS:
                return fallback

        client = self.client
        if client is None:
            return fallback

        try:
            result = await log_async_operation(
                logger,
                name=f"hot_memory.{operation}",
                intent=key,
                func=lambda: func(client),
                token_count=None,
                metadata=metadata,
            )
        except _REDIS_FAIL_OPEN_EXCEPTIONS as exc:
            self._log_degraded_operation(operation, key, exc)
            return fallback
        return result

    async def connect(self) -> None:
        if self.client is not None:
            return

        async with self._connect_lock:
            if self.client is not None:
                return

            async def _connect() -> None:
                pool = redis.ConnectionPool.from_url(
                    self.url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    health_check_interval=self.health_check_interval,
                    retry_on_timeout=self.retry_on_timeout,
                )
                self.client = redis.Redis(connection_pool=pool)

            try:
                await log_async_operation(
                    logger,
                    name="hot_memory.connect",
                    intent=self.url,
                    func=_connect,
                    token_count=None,
                    metadata={"url": self.url},
                )
            except _REDIS_FAIL_OPEN_EXCEPTIONS as exc:
                logger.warning(
                    "hot_memory.connect failed; url=%s error_type=%s error=%s",
                    self.url,
                    type(exc).__name__,
                    exc,
                )
                raise

    async def set(self, key: str, value: Any, ttl_seconds: int = 900) -> None:
        await self._run_fail_open(
            operation="set",
            key=key,
            fallback=None,
            metadata={"ttl": ttl_seconds},
            func=lambda client: client.set(key, value, ex=ttl_seconds),
        )

    async def get(self, key: str) -> str | None:
        return await self._run_fail_open(
            operation="get",
            key=key,
            fallback=None,
            metadata=None,
            func=lambda client: client.get(key),
        )
