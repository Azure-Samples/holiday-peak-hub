"""Pricing adapter stub."""
from typing import Any, Dict, Iterable, Optional

from .base import BaseAdapter


class PricingAdapter(BaseAdapter):
    """Adapter for pricing data sources."""

    def __init__(self) -> None:
        self.connected = False

    async def connect(self, **kwargs: Any) -> None:
        self.connected = True

    async def fetch(self, query: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        return [query]

    async def upsert(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.connected:
            await self.connect()
        return payload

    async def delete(self, identifier: str) -> bool:
        if not self.connected:
            await self.connect()
        return True
