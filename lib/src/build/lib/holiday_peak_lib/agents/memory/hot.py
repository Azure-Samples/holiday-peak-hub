"""Hot memory layer using Redis."""
from typing import Any, Optional

import redis.asyncio as redis

from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


logger = configure_logging()


class HotMemory:
    """Redis-backed hot memory for short-lived context."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        async def _connect():
            self.client = redis.from_url(self.url, encoding="utf-8", decode_responses=True)

        await log_async_operation(
            logger,
            name="hot_memory.connect",
            intent=self.url,
            func=_connect,
            metadata={"url": self.url},
        )

    async def set(self, key: str, value: Any, ttl_seconds: int = 900) -> None:
        if not self.client:
            await self.connect()
        await log_async_operation(
            logger,
            name="hot_memory.set",
            intent=key,
            func=lambda: self.client.set(key, value, ex=ttl_seconds),
            token_count=None,
            metadata={"ttl": ttl_seconds},
        )

    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            await self.connect()
        return await log_async_operation(
            logger,
            name="hot_memory.get",
            intent=key,
            func=lambda: self.client.get(key),
            token_count=None,
            metadata=None,
        )
