"""Memory builder with cascading read/write rules."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from .cold import ColdMemory
from .hot import HotMemory
from .warm import WarmMemory


@dataclass
class MemoryRules:
    """Rules controlling cascading memory behavior."""

    read_fallback: bool = True
    promote_on_read: bool = True
    write_through: bool = True
    hot_ttl_seconds: Optional[int] = 300
    warm_ttl_seconds: Optional[int] = None
    write_cold: bool = False


class MemoryClient:
    """Unified memory client with cascading read/write rules."""

    def __init__(
        self,
        *,
        hot: HotMemory | None = None,
        warm: WarmMemory | None = None,
        cold: ColdMemory | None = None,
        rules: MemoryRules | None = None,
    ) -> None:
        self.hot = hot
        self.warm = warm
        self.cold = cold
        self.rules = rules or MemoryRules()

    async def get(self, key: str) -> Any:
        if self.hot:
            value = await self.hot.get(key)
            if value is not None:
                return value

        if not self.rules.read_fallback:
            return None

        if self.warm:
            doc = await self.warm.read(item_id=key, partition_key=key)
            if doc is not None:
                value = doc.get("value", doc)
                if self.promote_to_hot() and self.hot:
                    await self.hot.set(key, value, ttl_seconds=self.rules.hot_ttl_seconds or 900)
                return value

        if self.cold:
            blob = await self.cold.download_text(key)
            if blob is None:
                return None
            value = blob.decode("utf-8") if isinstance(blob, (bytes, bytearray)) else blob
            if self.promote_to_hot() and self.hot:
                await self.hot.set(key, value, ttl_seconds=self.rules.hot_ttl_seconds or 900)
            if self.promote_to_warm() and self.warm:
                await self.warm.upsert(self._warm_item(key, value, ttl=self.rules.warm_ttl_seconds))
            return value
        return None

    async def set(self, key: str, value: Any) -> None:
        if self.hot:
            await self.hot.set(key, value, ttl_seconds=self.rules.hot_ttl_seconds or 900)

        if self.rules.write_through and self.warm:
            await self.warm.upsert(self._warm_item(key, value, ttl=self.rules.warm_ttl_seconds))

        if self.rules.write_cold and self.cold:
            payload = value if isinstance(value, str) else json.dumps(value)
            await self.cold.upload_text(key, payload)

    def promote_to_hot(self) -> bool:
        return self.rules.promote_on_read and self.hot is not None

    def promote_to_warm(self) -> bool:
        return self.rules.promote_on_read and self.warm is not None

    @staticmethod
    def _warm_item(key: str, value: Any, ttl: Optional[int]) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": key, "pk": key, "value": value}
        if ttl is not None:
            payload["ttl"] = ttl
        return payload


class MemoryBuilder:
    """Builder for cascading memory client configuration."""

    def __init__(self) -> None:
        self._hot: HotMemory | None = None
        self._warm: WarmMemory | None = None
        self._cold: ColdMemory | None = None
        self._rules = MemoryRules()

    def with_hot(self, hot: HotMemory | None) -> "MemoryBuilder":
        self._hot = hot
        return self

    def with_warm(self, warm: WarmMemory | None) -> "MemoryBuilder":
        self._warm = warm
        return self

    def with_cold(self, cold: ColdMemory | None) -> "MemoryBuilder":
        self._cold = cold
        return self

    def with_rules(
        self,
        *,
        read_fallback: bool | None = None,
        promote_on_read: bool | None = None,
        write_through: bool | None = None,
        hot_ttl_seconds: Optional[int] = None,
        warm_ttl_seconds: Optional[int] = None,
        write_cold: bool | None = None,
    ) -> "MemoryBuilder":
        if read_fallback is not None:
            self._rules.read_fallback = read_fallback
        if promote_on_read is not None:
            self._rules.promote_on_read = promote_on_read
        if write_through is not None:
            self._rules.write_through = write_through
        if hot_ttl_seconds is not None:
            self._rules.hot_ttl_seconds = hot_ttl_seconds
        if warm_ttl_seconds is not None:
            self._rules.warm_ttl_seconds = warm_ttl_seconds
        if write_cold is not None:
            self._rules.write_cold = write_cold
        return self

    def build(self) -> MemoryClient:
        if not any([self._hot, self._warm, self._cold]):
            raise ValueError("At least one memory tier must be configured")
        return MemoryClient(hot=self._hot, warm=self._warm, cold=self._cold, rules=self._rules)
