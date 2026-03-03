"""OAuth 2.0 and API Key authentication for SAP S/4HANA.

Supports two authentication modes:
- OAuth 2.0 Client Credentials (preferred for production)
- API Key via query parameter (for SAP API Business Hub sandbox)

Token caching avoids redundant round-trips to the token endpoint.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


class SAPS4HANAAuth:
    """Handles authentication for SAP S/4HANA REST/OData APIs.

    Reads credentials from environment variables. Token is cached
    and refreshed automatically when it expires.

    Environment variables
    ---------------------
    SAP_S4HANA_TOKEN_URL     OAuth 2.0 token endpoint
    SAP_S4HANA_CLIENT_ID     OAuth 2.0 client ID
    SAP_S4HANA_CLIENT_SECRET OAuth 2.0 client secret
    SAP_S4HANA_API_KEY       API key (takes precedence over OAuth 2.0)
    """

    _TOKEN_EXPIRY_BUFFER = 60  # seconds before expiry to refresh

    def __init__(
        self,
        *,
        token_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token_url = token_url or os.environ.get("SAP_S4HANA_TOKEN_URL", "")
        self._client_id = client_id or os.environ.get("SAP_S4HANA_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("SAP_S4HANA_CLIENT_SECRET", "")
        self._api_key = api_key or os.environ.get("SAP_S4HANA_API_KEY", "")
        self._transport = transport

        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def _token_is_valid(self) -> bool:
        return (
            self._access_token is not None
            and time.monotonic() < self._token_expires_at - self._TOKEN_EXPIRY_BUFFER
        )

    async def get_headers(self) -> dict[str, str]:
        """Return HTTP headers required for an authenticated request.

        Returns API-key header when an API key is configured, otherwise
        fetches (or reuses a cached) OAuth 2.0 bearer token.
        """
        if self._api_key:
            return {"APIKey": self._api_key}

        if not self._token_is_valid:
            await self._fetch_token()

        return {"Authorization": f"Bearer {self._access_token}"}

    async def _fetch_token(self) -> None:
        """Acquire a new OAuth 2.0 token via the client credentials flow."""
        if not self._token_url:
            raise ValueError("SAP_S4HANA_TOKEN_URL must be set for OAuth 2.0 authentication")
        if not self._client_id or not self._client_secret:
            raise ValueError("SAP_S4HANA_CLIENT_ID and SAP_S4HANA_CLIENT_SECRET must be set")

        request_data: dict[str, Any] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        async with httpx.AsyncClient(transport=self._transport) as client:
            response = await client.post(
                self._token_url,
                data=request_data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token_data = response.json()

        self._access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self._token_expires_at = time.monotonic() + expires_in

    def invalidate(self) -> None:
        """Force the next call to re-fetch a token."""
        self._access_token = None
        self._token_expires_at = 0.0
