"""Dynamics 365 Customer Engagement connector.

Implements ``CRMConnectorBase`` and ``BaseAdapter`` to integrate with the
Dynamics 365 CE OData v4 Web API.

Configuration is driven entirely by environment variables:

``D365_CE_BASE_URL``
    Full instance URL, e.g. ``https://org.crm.dynamics.com``.
``D365_CE_API_VERSION``
    OData API version (default ``9.2``).

Authentication uses :class:`~.auth.AzureADTokenProvider` which relies on
``DefaultAzureCredential`` and therefore respects the standard Azure SDK
environment variables (``AZURE_CLIENT_ID``, ``AZURE_CLIENT_SECRET``,
``AZURE_TENANT_ID``, managed identity, etc.).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Iterable, Optional

import httpx
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.integrations.contracts import (
    CRMConnectorBase,
    CustomerData,
    OrderData,
    SegmentData,
)

from .auth import AzureADTokenProvider
from .mappings import (
    map_contact_to_customer,
    map_marketinglist_to_segment,
    map_salesorder_to_order,
)

_DEFAULT_API_VERSION = "9.2"


class Dynamics365CEConnector(BaseAdapter, CRMConnectorBase):
    """Connector for Microsoft Dynamics 365 Customer Engagement.

    Connects to the OData v4 Web API exposed at
    ``{base_url}/api/data/v{api_version}/``.

    :param base_url: Dynamics 365 instance base URL.  Falls back to the
        ``D365_CE_BASE_URL`` environment variable when *None*.
    :param api_version: OData API version string (default ``9.2``).
    :param credential: Optional Azure identity credential.  Defaults to
        ``DefaultAzureCredential``.
    :param kwargs: Forwarded to :class:`~holiday_peak_lib.adapters.base.BaseAdapter`.

    Example — instantiation only (no real network I/O)::

        >>> c = Dynamics365CEConnector(base_url="https://org.crm.dynamics.com")
        >>> c._base_url
        'https://org.crm.dynamics.com'
        >>> c._api_base.endswith("/api/data/v9.2/")
        True
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_version: str = _DEFAULT_API_VERSION,
        credential=None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        resolved_url = (base_url or os.environ.get("D365_CE_BASE_URL", "")).rstrip("/")
        if not resolved_url:
            raise ValueError(
                "Dynamics 365 CE base URL must be provided via 'base_url' "
                "or the D365_CE_BASE_URL environment variable."
            )
        self._base_url = resolved_url
        self._api_version = api_version or os.environ.get(
            "D365_CE_API_VERSION", _DEFAULT_API_VERSION
        )
        self._api_base = f"{self._base_url}/api/data/v{self._api_version}/"
        self._token_provider = AzureADTokenProvider(
            resource_url=self._base_url,
            credential=credential,
        )
        self._http_client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # BaseAdapter hooks
    # ------------------------------------------------------------------

    async def _connect_impl(self, **kwargs: Any) -> None:
        """Initialise the shared ``httpx.AsyncClient``."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """Low-level fetch — delegates to :meth:`_odata_get`."""
        entity = query.get("_entity", "")
        params = {k: v for k, v in query.items() if not k.startswith("_") and v is not None}
        response = await self._odata_get(entity, params=params)
        return response.get("value", [response] if response and "value" not in response else [])

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """PATCH or POST a Dynamics 365 CE entity."""
        entity = payload.pop("_entity", "")
        entity_id = payload.pop("_id", None)
        if entity_id:
            path = f"{entity}({entity_id})"
            await self._odata_patch(path, payload)
            return {"id": entity_id}
        result = await self._odata_post(entity, payload)
        return result

    async def _delete_impl(self, identifier: str) -> bool:
        """Delete a Dynamics 365 CE entity record by logical path."""
        await self._odata_delete(identifier)
        return True

    # ------------------------------------------------------------------
    # CRMConnectorBase implementation
    # ------------------------------------------------------------------

    async def get_customer(self, customer_id: str) -> CustomerData | None:
        """Fetch a contact by its Dynamics 365 ``contactid``.

        :param customer_id: Dynamics 365 contact GUID.
        :returns: Canonical ``CustomerData`` or *None* if not found.
        """
        try:
            record = await self._odata_get(f"contacts({customer_id})")
        except AdapterError:
            return None
        if not record:
            return None
        return map_contact_to_customer(record)

    async def get_customer_by_email(self, email: str) -> CustomerData | None:
        """Find a contact by primary email address.

        :param email: Email address to search for.
        :returns: First matching ``CustomerData`` or *None*.
        """
        params = {
            "$filter": f"emailaddress1 eq '{email}'",
            "$top": "1",
        }
        response = await self._odata_get("contacts", params=params)
        records = response.get("value", [])
        if not records:
            return None
        return map_contact_to_customer(records[0])

    async def get_customer_segments(self, customer_id: str) -> list[SegmentData]:
        """List marketing lists that the contact belongs to.

        :param customer_id: Dynamics 365 contact GUID.
        :returns: List of canonical ``SegmentData`` objects.
        """
        path = f"contacts({customer_id})/listcontact_association"
        response = await self._odata_get(path)
        records = response.get("value", [])
        return [map_marketinglist_to_segment(r) for r in records]

    async def get_purchase_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderData]:
        """Retrieve sales orders linked to a contact.

        :param customer_id: Dynamics 365 contact GUID.
        :param since: Optional earliest creation date filter.
        :param limit: Maximum number of orders to return.
        :returns: List of canonical ``OrderData`` objects.
        """
        filter_parts = [f"customerid_contact/contactid eq {customer_id}"]
        if since:
            filter_parts.append(f"createdon ge {since.isoformat()}")
        params: dict[str, Any] = {
            "$filter": " and ".join(filter_parts),
            "$top": str(limit),
            "$orderby": "createdon desc",
        }
        response = await self._odata_get("salesorders", params=params)
        records = response.get("value", [])
        return [map_salesorder_to_order(r) for r in records]

    async def update_customer(self, customer_id: str, updates: dict) -> CustomerData:
        """PATCH a contact record and return the refreshed profile.

        :param customer_id: Dynamics 365 contact GUID.
        :param updates: Dict of field→value pairs to patch.
        :returns: Updated ``CustomerData``.
        :raises AdapterError: If the PATCH fails or the contact is missing.
        """
        await self._odata_patch(f"contacts({customer_id})", updates)
        customer = await self.get_customer(customer_id)
        if customer is None:
            raise AdapterError(f"Contact {customer_id!r} not found after update.")
        return customer

    async def track_event(self, customer_id: str, event_type: str, properties: dict) -> None:
        """Create a Dynamics 365 CE activity record for a customer event.

        Uses a custom ``new_customerevent`` entity (configurable via metadata).
        If the entity does not exist in the target org the call is a no-op.

        :param customer_id: Dynamics 365 contact GUID.
        :param event_type: Logical event name.
        :param properties: Arbitrary event properties.
        """
        payload = {
            "new_eventtype": event_type,
            "new_properties": str(properties),
            "regardingobjectid_contact@odata.bind": f"/contacts({customer_id})",
        }
        try:
            await self._odata_post("new_customerevents", payload)
        except AdapterError:
            # If the custom entity is absent, silently skip.
            pass

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        """Return connector health by probing the OData ``$metadata`` endpoint.

        :returns: Dict with ``ok`` bool and optional ``detail`` string.
        """
        try:
            await self._ensure_client()
            token = await self._token_provider.get_token()
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._api_base}$metadata",
                    headers={"Authorization": f"Bearer {token}"},
                )
            return {"ok": resp.status_code < 400}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "detail": str(exc)}

    # ------------------------------------------------------------------
    # OData helpers
    # ------------------------------------------------------------------

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)
        return self._http_client

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._token_provider.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Prefer": "odata.include-annotations=*",
        }

    async def _odata_get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        headers = await self._auth_headers()
        url = f"{self._api_base}{path}"
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 404:
            return {}
        if response.status_code >= 400:
            raise AdapterError(
                f"D365 CE GET {url!r} failed: {response.status_code} {response.text[:200]}"
            )
        return response.json()

    async def _odata_post(
        self,
        entity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        headers = await self._auth_headers()
        headers["Prefer"] = "return=representation"
        url = f"{self._api_base}{entity}"
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise AdapterError(
                f"D365 CE POST {url!r} failed: {response.status_code} {response.text[:200]}"
            )
        if response.status_code == 204:
            # Created with no body — return location header as dict
            location = response.headers.get("OData-EntityId", "")
            return {"OData-EntityId": location}
        return response.json()

    async def _odata_patch(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> None:
        client = await self._ensure_client()
        headers = await self._auth_headers()
        url = f"{self._api_base}{path}"
        response = await client.patch(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise AdapterError(
                f"D365 CE PATCH {url!r} failed: {response.status_code} {response.text[:200]}"
            )

    async def _odata_delete(self, path: str) -> None:
        client = await self._ensure_client()
        headers = await self._auth_headers()
        url = f"{self._api_base}{path}"
        response = await client.delete(url, headers=headers)
        if response.status_code >= 400:
            raise AdapterError(
                f"D365 CE DELETE {url!r} failed: {response.status_code} {response.text[:200]}"
            )
