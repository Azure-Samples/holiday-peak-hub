"""Oracle Fusion Cloud SCM connector.

Integrates with Oracle Fusion Cloud Supply Chain Management REST APIs to
provide canonical :class:`~holiday_peak_lib.connectors.common.protocols.InventoryData`
records to agents and services.

REST API reference (11.13.18.05):
- ``GET /fscmRestApi/resources/11.13.18.05/onHandQuantities``
- ``GET /fscmRestApi/resources/11.13.18.05/inventoryOrganizations``

Configuration via environment variables:
    ORACLE_SCM_BASE_URL      — Instance base URL, e.g. ``https://<host>``
    ORACLE_SCM_TOKEN_URL     — Token endpoint
    ORACLE_SCM_CLIENT_ID     — OAuth 2.0 client ID
    ORACLE_SCM_CLIENT_SECRET — OAuth 2.0 client secret
    ORACLE_SCM_SCOPE         — OAuth scopes (optional)
    ORACLE_SCM_API_VERSION   — REST resource version (default: ``11.13.18.05``)
    ORACLE_SCM_PAGE_SIZE     — Records per page (default: ``500``)
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

from holiday_peak_lib.adapters.base import AdapterError, BaseAdapter
from holiday_peak_lib.connectors.common.protocols import InventoryData
from holiday_peak_lib.connectors.inventory_scm.oracle_scm.auth import (
    OracleSCMAuth,
    OracleSCMAuthError,
)
from holiday_peak_lib.connectors.inventory_scm.oracle_scm.mappings import (
    map_on_hand_quantities,
    map_on_hand_quantity,
)


class InventoryConnectorBase(BaseAdapter, ABC):
    """Abstract base for SCM/inventory connectors.

    Subclasses must implement the high-level inventory query methods in
    addition to the low-level :class:`~holiday_peak_lib.adapters.base.BaseAdapter`
    hooks.
    """

    @abstractmethod
    async def get_on_hand_quantity(
        self,
        item_number: str,
        organization_code: Optional[str] = None,
    ) -> list[InventoryData]:
        """Return on-hand inventory records for *item_number*."""

    @abstractmethod
    async def list_on_hand_quantities(
        self,
        organization_code: Optional[str] = None,
        **filters: Any,
    ) -> list[InventoryData]:
        """Return all on-hand inventory records, optionally filtered."""

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return a health status dict for the connector."""


class OracleSCMConnector(InventoryConnectorBase):
    """Connector for Oracle Fusion Cloud SCM onHandQuantities REST API.

    Fetches and maps on-hand inventory data using OAuth 2.0 Client Credentials.
    Inherits circuit breaker, retry, rate-limit, and cache capabilities from
    :class:`~holiday_peak_lib.adapters.base.BaseAdapter`.

    Example (requires live Oracle instance):

        connector = OracleSCMConnector()
        records = await connector.get_on_hand_quantity("ITEM-001", "M1")
    """

    _DEFAULT_API_VERSION = "11.13.18.05"
    _DEFAULT_PAGE_SIZE = 500

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth: Optional[OracleSCMAuth] = None,
        api_version: Optional[str] = None,
        page_size: Optional[int] = None,
        http_timeout: float = 30.0,
        **adapter_kwargs: Any,
    ) -> None:
        super().__init__(timeout=http_timeout, **adapter_kwargs)
        self._base_url = (base_url or os.environ.get("ORACLE_SCM_BASE_URL", "")).rstrip("/")
        self._auth = auth or OracleSCMAuth()
        self._api_version = (
            api_version
            or os.environ.get("ORACLE_SCM_API_VERSION", self._DEFAULT_API_VERSION)
        )
        self._page_size = int(
            page_size or os.environ.get("ORACLE_SCM_PAGE_SIZE", self._DEFAULT_PAGE_SIZE)
        )

    # ------------------------------------------------------------------
    # BaseAdapter hooks
    # ------------------------------------------------------------------

    async def _connect_impl(self, **kwargs: Any) -> None:
        """Validate connectivity by obtaining an OAuth token."""
        await self._auth.get_token()

    async def _fetch_impl(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        """Dispatch fetch to the appropriate Oracle resource endpoint."""
        resource = query.get("resource", "onHandQuantities")
        if resource == "onHandQuantities":
            return await self._fetch_on_hand_quantities(
                item_number=query.get("item_number"),
                organization_code=query.get("organization_code"),
                extra_filters=query.get("extra_filters", {}),
            )
        raise AdapterError(f"Unknown Oracle SCM resource: {resource!r}")

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Oracle SCM is read-only via this connector; not implemented."""
        raise NotImplementedError("Oracle SCM connector does not support upsert.")

    async def _delete_impl(self, identifier: str) -> bool:
        """Oracle SCM is read-only via this connector; not implemented."""
        raise NotImplementedError("Oracle SCM connector does not support delete.")

    # ------------------------------------------------------------------
    # InventoryConnectorBase methods
    # ------------------------------------------------------------------

    async def get_on_hand_quantity(
        self,
        item_number: str,
        organization_code: Optional[str] = None,
    ) -> list[InventoryData]:
        """Return on-hand inventory records for a single item.

        Wraps the underlying adapter fetch with circuit-breaker / retry.

        Args:
            item_number: Oracle item number to query.
            organization_code: Optional inventory organization code filter.

        Returns:
            List of :class:`~holiday_peak_lib.connectors.common.protocols.InventoryData`
            records for the item.

        Raises:
            :class:`~holiday_peak_lib.adapters.base.AdapterError` on failure.
        """
        query: dict[str, Any] = {
            "resource": "onHandQuantities",
            "item_number": item_number,
        }
        if organization_code:
            query["organization_code"] = organization_code
        raw = await self.fetch(query)
        return map_on_hand_quantities(list(raw))

    async def list_on_hand_quantities(
        self,
        organization_code: Optional[str] = None,
        **filters: Any,
    ) -> list[InventoryData]:
        """Return all on-hand inventory records, with optional filters.

        Args:
            organization_code: Optional organization code to scope the query.
            **filters: Additional Oracle REST query filter key/value pairs.

        Returns:
            List of :class:`~holiday_peak_lib.connectors.common.protocols.InventoryData`.

        Raises:
            :class:`~holiday_peak_lib.adapters.base.AdapterError` on failure.
        """
        query: dict[str, Any] = {
            "resource": "onHandQuantities",
            "extra_filters": filters,
        }
        if organization_code:
            query["organization_code"] = organization_code
        raw = await self.fetch(query)
        return map_on_hand_quantities(list(raw))

    async def health(self) -> dict[str, Any]:
        """Return a health status dict for this connector.

        Returns ``{"status": "ok"}`` when the token endpoint is reachable and
        credentials are valid, or ``{"status": "error", "detail": <msg>}``
        otherwise.
        """
        try:
            await self._auth.get_token()
            return {"status": "ok", "connector": "oracle_scm"}
        except (OracleSCMAuthError, AdapterError) as exc:
            return {"status": "error", "connector": "oracle_scm", "detail": str(exc)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_headers(self) -> dict[str, str]:
        """Build authorised request headers."""
        token = await self._auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _resource_url(self, resource: str) -> str:
        """Build the full URL for an Oracle REST resource."""
        return f"{self._base_url}/fscmRestApi/resources/{self._api_version}/{resource}"

    def _build_filter(
        self,
        item_number: Optional[str],
        organization_code: Optional[str],
        extra_filters: dict[str, Any],
    ) -> Optional[str]:
        """Construct an Oracle SCIM-style finder/query filter string."""
        parts: list[str] = []
        if item_number:
            parts.append(f"ItemNumber='{item_number}'")
        if organization_code:
            parts.append(f"OrganizationCode='{organization_code}'")
        for key, value in extra_filters.items():
            parts.append(f"{key}='{value}'")
        return ";".join(parts) if parts else None

    async def _fetch_on_hand_quantities(
        self,
        item_number: Optional[str] = None,
        organization_code: Optional[str] = None,
        extra_filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Paginate through Oracle onHandQuantities and return raw records."""
        if not self._base_url:
            raise AdapterError(
                "ORACLE_SCM_BASE_URL is not configured."
            )

        headers = await self._get_headers()
        url = self._resource_url("onHandQuantities")
        q_filter = self._build_filter(item_number, organization_code, extra_filters or {})

        params: dict[str, Any] = {"limit": self._page_size, "offset": 0}
        if q_filter:
            params["q"] = q_filter

        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                try:
                    response = await client.get(url, headers=headers, params=params)
                    if response.status_code == 401:
                        self._auth.invalidate()
                        headers = await self._get_headers()
                        response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise AdapterError(
                        f"Oracle SCM API error {exc.response.status_code}: {exc.response.text}"
                    ) from exc
                except httpx.RequestError as exc:
                    raise AdapterError(f"Oracle SCM network error: {exc}") from exc

                body = response.json()
                items: list[dict[str, Any]] = body.get("items", [])
                results.extend(items)

                # Oracle REST uses hasMore + offset-based pagination
                if not body.get("hasMore", False):
                    break
                params["offset"] = params["offset"] + len(items)

        return results
