"""Braze Customer Engagement connector.

Implements :class:`CRMConnectorBase` backed by :class:`BaseAdapter` resilience
primitives (circuit breaker, retry, rate-limiting, caching).

Configuration via environment variables:
- ``BRAZE_BASE_URL``  – region-specific REST endpoint
                        (default: ``https://rest.iad-01.braze.com``)
- ``BRAZE_API_KEY``   – REST API key (Bearer token)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.integrations.contracts import (
    CRMConnectorBase,
    CustomerData,
    OrderData,
    SegmentData,
)

from .auth import BrazeAuth
from .mappings import (
    map_braze_purchase_to_order,
    map_braze_segment_to_segment,
    map_braze_user_to_customer,
)

_DEFAULT_BASE_URL = "https://rest.iad-01.braze.com"


class BrazeConnector(BaseAdapter, CRMConnectorBase):
    """Connector for the Braze Customer Engagement REST API.

    Extends :class:`BaseAdapter` to inherit rate-limiting, caching, retry, and
    circuit-breaker behaviour, and implements :class:`CRMConnectorBase` so that
    the connector can be consumed by any agent that depends on the CRM protocol.

    All HTTP communication uses :class:`httpx.AsyncClient`.  An optional
    ``transport`` parameter allows injection of a mock transport during tests.

    >>> import asyncio, httpx
    >>> transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"users": []}))
    >>> connector = BrazeConnector(api_key="key", transport=transport)
    >>> asyncio.run(connector.get_customer("u1")) is None
    True
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        **adapter_kwargs: Any,
    ) -> None:
        super().__init__(**adapter_kwargs)
        self._auth = BrazeAuth(api_key=api_key)
        self._base_url = (base_url or os.environ.get("BRAZE_BASE_URL", _DEFAULT_BASE_URL)).rstrip(
            "/"
        )
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            kwargs: dict[str, Any] = {
                "base_url": self._base_url,
                "headers": self._auth.headers,
                "timeout": self._timeout,
            }
            if self._transport is not None:
                kwargs["transport"] = self._transport
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def _get(self, path: str, params: dict | None = None) -> Any:
        client = self._get_client()
        resp = await client.get(path, params=params)
        self._raise_for_status(resp)
        return resp.json()

    async def _post(self, path: str, json: dict) -> Any:
        client = self._get_client()
        resp = await client.post(path, json=json)
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 429:
            raise AdapterError("Braze rate limit exceeded")
        if response.status_code == 401:
            raise AdapterError("Braze authentication failed – check BRAZE_API_KEY")
        if response.is_error:
            raise AdapterError(f"Braze API error {response.status_code}: {response.text[:200]}")

    # ------------------------------------------------------------------
    # BaseAdapter abstract hooks
    # ------------------------------------------------------------------

    async def _connect_impl(self, **kwargs: Any) -> None:
        """Initialise the HTTP client (lazy – actual connection happens on first request)."""
        self._get_client()

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """Dispatch to the appropriate Braze endpoint based on ``query["_op"]``."""
        op = query.get("_op")
        if op == "export_users":
            return await self._export_users(query.get("external_ids", []))
        if op == "campaigns":
            return await self._list_campaigns(
                query.get("page", 0), query.get("include_archived", False)
            )
        if op == "segments":
            return await self._list_segments(query.get("page", 0))
        raise AdapterError(f"Unknown Braze fetch operation: {op!r}")

    async def _upsert_impl(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch to ``/users/track`` or ``/messages/send`` based on ``payload["_op"]``."""
        op = payload.get("_op")
        if op == "track":
            return await self._track(payload.get("body", {}))
        if op == "send_message":
            return await self._send_message(payload.get("body", {}))
        raise AdapterError(f"Unknown Braze upsert operation: {op!r}")

    async def _delete_impl(self, identifier: str) -> bool:
        """Braze does not expose a generic delete in the public REST API."""
        raise AdapterError("Delete is not supported by the Braze REST API")

    # ------------------------------------------------------------------
    # Low-level Braze API calls
    # ------------------------------------------------------------------

    async def _export_users(self, external_ids: list[str]) -> list[dict]:
        data = await self._post(
            "/users/export/ids", {"external_ids": external_ids, "fields_to_export": []}
        )
        return data.get("users", [])

    async def _list_campaigns(self, page: int = 0, include_archived: bool = False) -> list[dict]:
        data = await self._get(
            "/campaigns/list",
            params={"page": page, "include_archived": str(include_archived).lower()},
        )
        return data.get("campaigns", [])

    async def _list_segments(self, page: int = 0) -> list[dict]:
        data = await self._get("/segments/list", params={"page": page})
        return data.get("segments", [])

    async def _track(self, body: dict) -> dict:
        return await self._post("/users/track", body)

    async def _send_message(self, body: dict) -> dict:
        return await self._post("/messages/send", body)

    # ------------------------------------------------------------------
    # CRMConnectorBase public interface
    # ------------------------------------------------------------------

    async def get_customer(self, customer_id: str) -> CustomerData | None:
        """Fetch a single customer by external ID.

        Returns ``None`` when the user is not found in Braze.
        """
        users = await self._export_users([customer_id])
        if not users:
            return None
        return map_braze_user_to_customer(users[0])

    async def get_customer_by_email(self, email: str) -> CustomerData | None:
        """Look up a customer by e-mail address using the export endpoint."""
        data = await self._post(
            "/users/export/ids", {"email_address": email, "fields_to_export": []}
        )
        users = data.get("users", [])
        if not users:
            return None
        return map_braze_user_to_customer(users[0])

    async def get_customer_segments(self, customer_id: str) -> list[SegmentData]:
        """Return all segments the customer belongs to.

        Braze does not expose per-user segment membership directly, so this
        method returns all segments from ``/segments/list`` and filters by
        the ``membership`` field when present.
        """
        raw_segments = await self._list_segments()
        customer_data = await self.get_customer(customer_id)
        if customer_data is None:
            return []
        customer_segments = set(customer_data.segments)
        result: list[SegmentData] = []
        for raw in raw_segments:
            seg = map_braze_segment_to_segment(raw)
            if not customer_segments or seg.name in customer_segments:
                result.append(seg)
        return result

    async def get_purchase_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderData]:
        """Return the purchase history for a customer as :class:`OrderData` objects."""
        users = await self._export_users([customer_id])
        if not users:
            return []
        purchases = users[0].get("purchases") or []
        orders: list[OrderData] = []
        for purchase in purchases[:limit]:
            order = map_braze_purchase_to_order(purchase)
            if since and order.created_at and order.created_at < since:
                continue
            orders.append(order)
        return orders

    async def update_customer(self, customer_id: str, updates: dict) -> CustomerData:
        """Update customer attributes via ``/users/track``."""
        body = {
            "attributes": [{"external_id": customer_id, **updates}],
        }
        await self._track(body)
        customer = await self.get_customer(customer_id)
        if customer is None:
            raise AdapterError(f"Customer '{customer_id}' not found after update")
        return customer

    async def track_event(self, customer_id: str, event_type: str, properties: dict) -> None:
        """Track a custom event for the given customer via ``/users/track``."""
        body = {
            "events": [
                {
                    "external_id": customer_id,
                    "name": event_type,
                    "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "properties": properties,
                }
            ]
        }
        await self._track(body)

    # ------------------------------------------------------------------
    # Extra Braze-specific methods (beyond CRMConnectorBase)
    # ------------------------------------------------------------------

    async def list_campaigns(self, page: int = 0, include_archived: bool = False) -> list[dict]:
        """Return campaign list from Braze (raw dicts).

        :param page: Zero-based page index for pagination.
        :param include_archived: Whether to include archived campaigns.
        """
        return await self._list_campaigns(page=page, include_archived=include_archived)

    async def send_message(
        self,
        *,
        campaign_id: str | None = None,
        recipients: list[dict] | None = None,
        messages: dict | None = None,
    ) -> dict:
        """Send a message via ``/messages/send``.

        :param campaign_id: Optional campaign ID to associate the message with.
        :param recipients: List of recipient objects (``external_user_id`` etc.).
        :param messages: Platform-specific message objects (push, email, etc.).
        :returns: The raw Braze API response dict.
        """
        body: dict[str, Any] = {}
        if campaign_id:
            body["campaign_id"] = campaign_id
        if recipients:
            body["recipients"] = recipients
        if messages:
            body["messages"] = messages
        return await self._send_message(body)

    async def health(self) -> dict:
        """Return a basic health status by probing the segments endpoint."""
        try:
            await self._list_segments(page=0)
            return {"ok": True, "connector": "braze"}
        except AdapterError as exc:
            return {"ok": False, "connector": "braze", "error": str(exc)}
