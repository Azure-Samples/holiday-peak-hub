"""Mock adapters returning deterministic data for connectors.

These stubs satisfy `BaseAdapter` for development and doctest use. They emit
static payloads matching connector expectations, enabling quick agent context
assembly without external systems.
"""

import datetime as _dt
from typing import Any, Iterable, Optional

from holiday_peak_lib.adapters.base import BaseAdapter


class MockProductAdapter(BaseAdapter):
    """Mock product adapter returning a single product and related items.

    >>> import asyncio
    >>> adapter = MockProductAdapter()
    >>> list(asyncio.run(adapter.fetch({"entity": "product", "sku": "SKU-1"})))[0]["sku"]
    'SKU-1'
    """

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if query.get("entity") == "product":
            sku = query.get("sku", "SKU-1")
            return [{"sku": sku, "name": "Mock Product", "price": 10.0, "currency": "USD"}]
        if query.get("entity") == "related":
            return [
                {"sku": "SKU-REL-1", "name": "Mock Related A", "price": 8.0, "currency": "USD"},
                {"sku": "SKU-REL-2", "name": "Mock Related B", "price": 12.0, "currency": "USD"},
            ]
        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True


class MockPricingAdapter(BaseAdapter):
    """Mock pricing adapter returning fixed offers.

    >>> import asyncio
    >>> adapter = MockPricingAdapter()
    >>> offers = list(asyncio.run(adapter.fetch({"entity": "price", "sku": "SKU-1"})))
    >>> offers[0]["currency"]
    'USD'
    """

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        sku = query.get("sku", "SKU-1")
        if query.get("entity") == "price":
            return [
                {"sku": sku, "currency": "USD", "amount": 9.5, "promotional": True},
                {"sku": sku, "currency": "USD", "amount": 10.0, "promotional": False},
            ]
        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True


class MockInventoryAdapter(BaseAdapter):
    """Mock inventory adapter returning stock and warehouse availability.

    >>> import asyncio
    >>> adapter = MockInventoryAdapter()
    >>> list(asyncio.run(adapter.fetch({"entity": "inventory", "sku": "SKU-1"})))[0]["available"]
    5
    """

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        sku = query.get("sku", "SKU-1")
        if query.get("entity") == "inventory":
            return [{"sku": sku, "available": 5, "reserved": 0}]
        if query.get("entity") == "warehouse_stock":
            return [
                {"sku": sku, "warehouse_id": "W1", "available": 3},
                {"sku": sku, "warehouse_id": "W2", "available": 2},
            ]
        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True


class MockLogisticsAdapter(BaseAdapter):
    """Mock logistics adapter returning a shipment and events.

    >>> import asyncio
    >>> adapter = MockLogisticsAdapter()
    >>> list(asyncio.run(adapter.fetch({"entity": "shipment", "tracking_id": "T1"})))[0]["status"]
    'in_transit'
    """

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if query.get("entity") == "shipment":
            return [
                {
                    "tracking_id": query.get("tracking_id", "T1"),
                    "status": "in_transit",
                    "origin": "Origin",
                    "destination": "Destination",
                }
            ]
        if query.get("entity") == "events":
            now = _dt.datetime.utcnow()
            return [
                {"code": "PU", "occurred_at": now},
                {"code": "IT", "occurred_at": now},
            ]
        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True


class MockCRMAdapter(BaseAdapter):
    """Mock CRM adapter returning contacts, accounts, and interactions.

    >>> import asyncio
    >>> adapter = MockCRMAdapter()
    >>> list(asyncio.run(adapter.fetch({"entity": "contact", "id": "c1"})))[0]["contact_id"]
    'c1'
    """

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if query.get("entity") == "contact":
            cid = query.get("id", "c1")
            return [{"contact_id": cid, "account_id": "a1", "email": "c1@example.com"}]
        if query.get("entity") == "account":
            aid = query.get("id", "a1")
            return [{"account_id": aid, "name": "Mock Account"}]
        if query.get("entity") == "interaction":
            cid = query.get("contact_id", "c1")
            return [
                {
                    "interaction_id": "i1",
                    "contact_id": cid,
                    "channel": "email",
                    "occurred_at": _dt.datetime.utcnow(),
                }
            ]
        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True


class MockFunnelAdapter(BaseAdapter):
    """Mock funnel adapter returning funnel metrics.

    >>> import asyncio
    >>> adapter = MockFunnelAdapter()
    >>> list(asyncio.run(adapter.fetch({"entity": "funnel", "campaign_id": "cmp"})))[0]["stage"]
    'view'
    """

    async def _connect_impl(self, **kwargs: Any) -> None:
        return None

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if query.get("entity") == "funnel":
            return [
                {"stage": "view", "count": 100},
                {"stage": "click", "count": 25},
            ]
        return []

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        return payload

    async def _delete_impl(self, identifier: str) -> bool:
        return True
