"""Salesforce CRM & Marketing Cloud connector.

Implements ``CRMConnectorBase`` against the Salesforce REST API v59.0.

API features used:
- SOQL via ``/services/data/{version}/query``
- sObject CRUD via ``/services/data/{version}/sobjects``
- Platform Events for Marketing Cloud engagement tracking

Environment variables:
    SALESFORCE_CLIENT_ID        Connected App consumer key
    SALESFORCE_CLIENT_SECRET    Connected App consumer secret
    SALESFORCE_USERNAME         Salesforce username
    SALESFORCE_PASSWORD         Salesforce password + security token
    SALESFORCE_LOGIN_URL        Defaults to https://login.salesforce.com
    SALESFORCE_API_VERSION      Defaults to v59.0
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

import httpx

from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.integrations.contracts import (
    CRMConnectorBase,
    CustomerData,
    OrderData,
    SegmentData,
)

from .auth import SalesforceAuth
from .mappings import (
    map_campaign_to_segment,
    map_contact_to_customer,
    map_order_to_order_data,
)

_DEFAULT_API_VERSION = "v59.0"


def _sanitize_soql_value(value: str) -> str:
    """Escape single quotes in a SOQL string literal to prevent injection."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class SalesforceCRMConnector(CRMConnectorBase):
    """Salesforce CRM REST API connector.

    Provides customer 360, service cases, loyalty segments, and order history
    by querying Salesforce CRM objects via SOQL and the REST sObject API.

    Example instantiation (credentials supplied via env vars)::

        connector = SalesforceCRMConnector()
        customer = await connector.get_customer("003xx000004TmiKAAS")
    """

    def __init__(
        self,
        *,
        auth: Optional[SalesforceAuth] = None,
        api_version: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._auth = auth or SalesforceAuth()
        self._api_version = (
            api_version
            or os.environ.get("SALESFORCE_API_VERSION", _DEFAULT_API_VERSION)
        )
        self._http_client = http_client
        self._owns_client = http_client is None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "SalesforceCRMConnector":
        if self._owns_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _data_url(self, instance_url: str) -> str:
        return f"{instance_url}/services/data/{self._api_version}"

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        token_entry = await self._auth.get_token()
        headers = {
            "Authorization": f"Bearer {token_entry.access_token}",
            "Content-Type": "application/json",
        }
        base = self._data_url(token_entry.instance_url)
        client = self._http_client
        if client is None:
            raise AdapterError("HTTP client not initialised; use async context manager")
        response = await client.get(f"{base}{path}", headers=headers, params=params or {})
        if response.status_code == 401:
            self._auth.invalidate()
            raise AdapterError("Salesforce authentication failed (401)")
        if response.status_code == 429:
            raise AdapterError("Salesforce rate limit exceeded (429)")
        response.raise_for_status()
        return response.json()

    async def _patch(self, path: str, payload: dict) -> None:
        token_entry = await self._auth.get_token()
        headers = {
            "Authorization": f"Bearer {token_entry.access_token}",
            "Content-Type": "application/json",
        }
        base = self._data_url(token_entry.instance_url)
        client = self._http_client
        if client is None:
            raise AdapterError("HTTP client not initialised; use async context manager")
        response = await client.patch(f"{base}{path}", headers=headers, json=payload)
        if response.status_code == 401:
            self._auth.invalidate()
            raise AdapterError("Salesforce authentication failed (401)")
        response.raise_for_status()

    async def _post(self, path: str, payload: dict) -> dict[str, Any]:
        token_entry = await self._auth.get_token()
        headers = {
            "Authorization": f"Bearer {token_entry.access_token}",
            "Content-Type": "application/json",
        }
        base = self._data_url(token_entry.instance_url)
        client = self._http_client
        if client is None:
            raise AdapterError("HTTP client not initialised; use async context manager")
        response = await client.post(f"{base}{path}", headers=headers, json=payload)
        if response.status_code == 401:
            self._auth.invalidate()
            raise AdapterError("Salesforce authentication failed (401)")
        response.raise_for_status()
        return response.json() if response.content else {}

    async def _soql(self, query: str) -> list[dict[str, Any]]:
        """Execute a SOQL query and return all records (handles pagination)."""
        records: list[dict[str, Any]] = []
        params: dict[str, str] = {"q": query}
        path = "/query"

        while True:
            data = await self._get(path, params=params)
            records.extend(data.get("records", []))
            if data.get("done", True):
                break
            next_url: str = data["nextRecordsUrl"]
            # nextRecordsUrl is relative to instance root, e.g.
            # /services/data/v59.0/query/01gxx...
            path = next_url.split(f"/{self._api_version}")[-1]
            params = {}

        return records

    # ------------------------------------------------------------------
    # CRMConnectorBase implementation
    # ------------------------------------------------------------------
    async def get_customer(self, customer_id: str) -> CustomerData | None:
        """Fetch a Salesforce Contact by Id."""
        soql = (
            "SELECT Id, Email, FirstName, LastName, Phone, "
            "loyalty_tier__c, Segments__c, HasOptedOutOfEmail, HasOptedOutOfFax, "
            "LastActivityDate, npo02__TotalOppAmount__c "
            f"FROM Contact WHERE Id = '{_sanitize_soql_value(customer_id)}' LIMIT 1"
        )
        records = await self._soql(soql)
        return map_contact_to_customer(records[0]) if records else None

    async def get_customer_by_email(self, email: str) -> CustomerData | None:
        """Find a Salesforce Contact by email address."""
        safe_email = email.replace("\\", "\\\\").replace("'", "\\'")
        soql = (
            "SELECT Id, Email, FirstName, LastName, Phone, "
            "loyalty_tier__c, Segments__c, HasOptedOutOfEmail, HasOptedOutOfFax, "
            "LastActivityDate, npo02__TotalOppAmount__c "
            f"FROM Contact WHERE Email = '{safe_email}' LIMIT 1"
        )
        records = await self._soql(soql)
        return map_contact_to_customer(records[0]) if records else None

    async def get_customer_segments(self, customer_id: str) -> list[SegmentData]:
        """Return Salesforce Campaigns a Contact is a member of."""
        soql = (
            "SELECT CampaignId, Campaign.Id, Campaign.Name, Campaign.Description, "
            "Campaign.Type, Campaign.Status, Campaign.StartDate, Campaign.EndDate, "
            "Campaign.NumberOfContacts "
            f"FROM CampaignMember WHERE ContactId = '{_sanitize_soql_value(customer_id)}'"
        )
        records = await self._soql(soql)
        segments: list[SegmentData] = []
        for rec in records:
            campaign = rec.get("Campaign") or {}
            if campaign:
                segments.append(map_campaign_to_segment(campaign))
        return segments

    async def get_purchase_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderData]:
        """Retrieve Salesforce Orders linked to the customer's Account."""
        where_clauses = [f"AccountId = '{_sanitize_soql_value(customer_id)}'"]
        if since is not None:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            where_clauses.append(f"CreatedDate >= {since_str}")
        where = " AND ".join(where_clauses)
        soql = (
            "SELECT Id, AccountId, Status, TotalAmount, CurrencyIsoCode, "
            "CreatedDate, LastModifiedDate, ShipToContactId, "
            "(SELECT Product2Id, ProductCode, Description, Quantity, UnitPrice, TotalPrice "
            "FROM OrderItems) "
            f"FROM Order WHERE {where} "
            f"ORDER BY CreatedDate DESC LIMIT {limit}"
        )
        records = await self._soql(soql)
        return [map_order_to_order_data(r) for r in records]

    async def update_customer(self, customer_id: str, updates: dict) -> CustomerData:
        """Patch a Salesforce Contact and return the refreshed record."""
        await self._patch(f"/sobjects/Contact/{customer_id}", updates)
        result = await self.get_customer(customer_id)
        if result is None:
            raise AdapterError(f"Contact '{customer_id}' not found after update")
        return result

    async def track_event(
        self, customer_id: str, event_type: str, properties: dict
    ) -> None:
        """Publish a Platform Event for Marketing Cloud journey activation.

        Salesforce Platform Event object: ``Retail_Engagement__e``
        """
        event_payload = {
            "Customer_Id__c": customer_id,
            "Event_Type__c": event_type,
            "Properties__c": str(properties),
        }
        await self._post("/sobjects/Retail_Engagement__e", event_payload)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    async def health(self) -> dict[str, Any]:
        """Verify connectivity by querying the Salesforce limits endpoint."""
        try:
            token_entry = await self._auth.get_token()
            client = self._http_client
            if client is None:
                raise AdapterError("HTTP client not initialised")
            headers = {"Authorization": f"Bearer {token_entry.access_token}"}
            base = self._data_url(token_entry.instance_url)
            resp = await client.get(f"{base}/limits", headers=headers, timeout=10.0)
            resp.raise_for_status()
            return {"ok": True, "status_code": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
