"""Adobe Experience Platform (AEP) CRM connector.

Implements ``CRMConnectorBase`` against the Adobe Experience Platform
REST APIs:

- Profile Access  – ``GET /data/core/ups/access/entities``
- Profile Preview – ``GET /data/core/ups/preview/sample``
- Audiences       – ``GET /segmentation/audiences``
- Profile Export  – ``POST /data/core/ups/export/jobs``
- Data Ingestion  – ``POST /collection/{inlet_id}``

Authentication uses Adobe IMS OAuth 2.0 client-credentials flow
(see ``auth.py``).

Configuration via environment variables:

- ``AEP_BASE_URL``        – Platform API base URL
                            (default: ``https://platform.adobe.io``)
- ``AEP_ORG_ID``          – IMS org ID
- ``AEP_SANDBOX_NAME``    – Sandbox name (default: ``prod``)
- ``AEP_CLIENT_ID``       – OAuth client ID
- ``AEP_CLIENT_SECRET``   – OAuth client secret
- ``AEP_INLET_ID``        – Streaming inlet ID for data ingestion
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Iterable, Optional

import httpx
from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.connectors.crm_loyalty.adobe_aep.auth import AdobeImsAuth
from holiday_peak_lib.connectors.crm_loyalty.adobe_aep.mappings import (
    audience_to_segment,
    export_record_to_order,
    xdm_to_customer,
)
from holiday_peak_lib.integrations.contracts import (
    CRMConnectorBase,
    CustomerData,
    OrderData,
    SegmentData,
)


class _AEPHttpAdapter(BaseAdapter):
    """Low-level BaseAdapter that delegates HTTP calls to ``httpx``."""

    def __init__(self, base_url: str, auth: AdobeImsAuth, org_id: str, sandbox: str) -> None:
        super().__init__(
            max_calls=20,
            per_seconds=1.0,
            cache_ttl=60.0,
            retries=3,
            timeout=30.0,
        )
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._org_id = org_id
        self._sandbox = sandbox

    async def _connect_impl(self, **kwargs: Any) -> None:
        """No persistent connection needed for REST."""

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """Execute a GET request; ``query`` must contain ``_path``."""
        path: str = query.pop("_path")
        headers = await self._build_headers()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}{path}", headers=headers, params=query or None
            )
            self._raise_for_status(response)
            return [response.json()]

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Execute a POST request; ``payload`` must contain ``_path``."""
        path: str = payload.pop("_path")
        headers = await self._build_headers()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}{path}", headers=headers, json=payload or None
            )
            self._raise_for_status(response)
            body = response.text
            return response.json() if body else {}

    async def _delete_impl(self, identifier: str) -> bool:
        raise NotImplementedError("AEP connector does not support delete via BaseAdapter")

    async def _build_headers(self) -> dict[str, str]:
        token = await self._auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": self._auth.client_id,
            "x-gw-ims-org-id": self._org_id,
            "x-sandbox-name": self._sandbox,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise AdapterError("AEP authentication failed – check credentials")
        if response.status_code == 429:
            raise AdapterError("AEP rate limit exceeded")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AdapterError(f"AEP API error {response.status_code}") from exc


class AdobeAEPConnector(CRMConnectorBase):
    """Adobe Experience Platform CRM connector.

    Implements the full ``CRMConnectorBase`` interface using the AEP
    Profile Access, Segmentation, and Data Ingestion REST APIs.

    Example::

        connector = AdobeAEPConnector()
        customer = await connector.get_customer("some-profile-id")
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        org_id: Optional[str] = None,
        sandbox: Optional[str] = None,
        inlet_id: Optional[str] = None,
        auth: Optional[AdobeImsAuth] = None,
    ) -> None:
        self._base_url = (
            base_url or os.environ.get("AEP_BASE_URL", "https://platform.adobe.io")
        ).rstrip("/")
        self._org_id = org_id or os.environ.get("AEP_ORG_ID", "")
        self._sandbox = sandbox or os.environ.get("AEP_SANDBOX_NAME", "prod")
        self._inlet_id = inlet_id or os.environ.get("AEP_INLET_ID", "")
        self._auth = auth or AdobeImsAuth()
        self._http = _AEPHttpAdapter(
            base_url=self._base_url,
            auth=self._auth,
            org_id=self._org_id,
            sandbox=self._sandbox,
        )

    # ------------------------------------------------------------------
    # CRMConnectorBase interface
    # ------------------------------------------------------------------

    async def get_customer(self, customer_id: str) -> CustomerData | None:
        """Fetch a profile from the Unified Profile Service by entity ID."""
        try:
            results = await self._http.fetch(
                {
                    "_path": "/data/core/ups/access/entities",
                    "schema.name": "_xdm.context.profile",
                    "entityId": customer_id,
                    "entityIdNS": "ECID",
                }
            )
            raw = list(results)[0]
            entities = raw.get("entities", [raw])
            if not entities:
                return None
            return xdm_to_customer(entities[0])
        except AdapterError:
            return None

    async def get_customer_by_email(self, email: str) -> CustomerData | None:
        """Look up a profile by email address."""
        try:
            results = await self._http.fetch(
                {
                    "_path": "/data/core/ups/access/entities",
                    "schema.name": "_xdm.context.profile",
                    "entityId": email,
                    "entityIdNS": "Email",
                }
            )
            raw = list(results)[0]
            entities = raw.get("entities", [raw])
            if not entities:
                return None
            return xdm_to_customer(entities[0])
        except AdapterError:
            return None

    async def get_customer_segments(self, customer_id: str) -> list[SegmentData]:
        """Return segment memberships for a given profile."""
        customer = await self.get_customer(customer_id)
        if customer is None:
            return []
        segment_ids = customer.segments
        if not segment_ids:
            return []
        all_segments = await self.list_audiences()
        return [s for s in all_segments if s.segment_id in segment_ids]

    async def get_purchase_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderData]:
        """Retrieve purchase history via a Profile Export job."""
        job_payload: dict[str, Any] = {
            "_path": "/data/core/ups/export/jobs",
            "fields": "personalEmail,commerce,productListItems,endUserIDs,timestamp",
            "mergePolicy": {"id": "timestampOrdered"},
            "filter": {
                "segments": [],
                "fromIngestTimestamp": (since.isoformat() if since else "1970-01-01T00:00:00Z"),
            },
            "destinationDatasetId": f"export_{customer_id}",
        }
        try:
            result = await self._http.upsert(job_payload)
            records: list[dict[str, Any]] = result.get("records", [])
            return [export_record_to_order(r) for r in records[:limit]]
        except AdapterError:
            return []

    async def update_customer(self, customer_id: str, updates: dict) -> CustomerData:
        """Stream an XDM patch event via the Streaming Ingestion API."""
        inlet_path = f"/collection/{self._inlet_id}"
        payload: dict[str, Any] = {
            "_path": inlet_path,
            "header": {
                "schemaRef": {
                    "id": "https://ns.adobe.com/xdm/context/profile",
                    "contentType": "application/vnd.adobe.xed-full+json; version=1",
                },
                "imsOrgId": self._org_id,
                "datasetId": updates.pop("datasetId", ""),
                "source": {"name": "holiday-peak-hub"},
            },
            "body": {
                "xdmMeta": {
                    "schemaRef": {
                        "id": "https://ns.adobe.com/xdm/context/profile",
                        "contentType": "application/vnd.adobe.xed-full+json; version=1",
                    }
                },
                "xdmEntity": {"_id": customer_id, **updates},
            },
        }
        await self._http.upsert(payload)
        updated = await self.get_customer(customer_id)
        if updated is None:
            raise AdapterError(f"Profile '{customer_id}' not found after update")
        return updated

    async def track_event(self, customer_id: str, event_type: str, properties: dict) -> None:
        """Ingest an XDM ExperienceEvent via the Streaming Ingestion API."""
        inlet_path = f"/collection/{self._inlet_id}"
        payload: dict[str, Any] = {
            "_path": inlet_path,
            "header": {
                "schemaRef": {
                    "id": "https://ns.adobe.com/xdm/context/experienceevent",
                    "contentType": "application/vnd.adobe.xed-full+json; version=1",
                },
                "imsOrgId": self._org_id,
                "datasetId": properties.pop("datasetId", ""),
                "source": {"name": "holiday-peak-hub"},
            },
            "body": {
                "xdmMeta": {
                    "schemaRef": {
                        "id": "https://ns.adobe.com/xdm/context/experienceevent",
                        "contentType": "application/vnd.adobe.xed-full+json; version=1",
                    }
                },
                "xdmEntity": {
                    "_id": customer_id,
                    "eventType": event_type,
                    **properties,
                },
            },
        }
        await self._http.upsert(payload)

    # ------------------------------------------------------------------
    # AEP-specific methods
    # ------------------------------------------------------------------

    async def list_audiences(self, *, limit: int = 100, start: int = 0) -> list[SegmentData]:
        """Return a page of AEP audiences."""
        try:
            results = await self._http.fetch(
                {
                    "_path": "/segmentation/audiences",
                    "limit": limit,
                    "start": start,
                }
            )
            raw = list(results)[0]
            audiences: list[dict[str, Any]] = raw.get("children", raw.get("segments", []))
            return [audience_to_segment(a) for a in audiences]
        except AdapterError:
            return []

    async def get_profile_preview(self, *, limit: int = 20) -> list[CustomerData]:
        """Return a sample of profiles from the preview API."""
        try:
            results = await self._http.fetch(
                {
                    "_path": "/data/core/ups/preview/sample",
                    "limit": limit,
                }
            )
            raw = list(results)[0]
            entities: list[dict[str, Any]] = raw.get("entities", [raw])
            return [xdm_to_customer(e) for e in entities]
        except AdapterError:
            return []

    async def health(self) -> dict[str, Any]:
        """Check connectivity by retrieving a minimal profile preview."""
        try:
            await self._http.fetch({"_path": "/data/core/ups/preview/sample", "limit": 1})
            return {"ok": True, "connector": "adobe_aep"}
        except AdapterError as exc:
            return {"ok": False, "connector": "adobe_aep", "error": str(exc)}
