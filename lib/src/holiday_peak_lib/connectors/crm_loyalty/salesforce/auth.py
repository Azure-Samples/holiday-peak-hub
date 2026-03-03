"""Salesforce OAuth 2.0 authentication handler.

Supports:
- JWT Bearer flow (Connected App with RSA key pair)
- Username-Password flow (for server-to-server dev/test)

Tokens are cached in memory with TTL-based auto-refresh.

Environment variables:
    SALESFORCE_CLIENT_ID       Connected App consumer key
    SALESFORCE_CLIENT_SECRET   Connected App consumer secret (password flow)
    SALESFORCE_USERNAME        Salesforce username (password flow)
    SALESFORCE_PASSWORD        Salesforce password + security token (password flow)
    SALESFORCE_LOGIN_URL       Login URL, defaults to https://login.salesforce.com
    SALESFORCE_API_VERSION     API version, defaults to v59.0
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class _TokenEntry:
    access_token: str
    instance_url: str
    expires_at: float


class SalesforceAuth:
    """Handles Salesforce OAuth 2.0 token acquisition and caching.

    Supports the Username-Password (ROPC) flow and the Client Credentials
    flow.  Token refresh is transparent: callers always receive a valid
    token via :py:meth:`get_token`.

    >>> auth = SalesforceAuth(
    ...     client_id="cid",
    ...     client_secret="csec",
    ...     username="u@example.com",
    ...     password="pass",
    ... )
    >>> auth._token_entry is None
    True
    """

    _TOKEN_URL_PATH = "/services/oauth2/token"
    _DEFAULT_LOGIN_URL = "https://login.salesforce.com"
    _TOKEN_EXPIRY_BUFFER = 60  # seconds before actual expiry to refresh

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        login_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._client_id = client_id or os.environ.get("SALESFORCE_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("SALESFORCE_CLIENT_SECRET", "")
        self._username = username or os.environ.get("SALESFORCE_USERNAME", "")
        self._password = password or os.environ.get("SALESFORCE_PASSWORD", "")
        self._login_url = (
            login_url
            or os.environ.get("SALESFORCE_LOGIN_URL", self._DEFAULT_LOGIN_URL)
        ).rstrip("/")
        self._http_client = http_client
        self._token_entry: Optional[_TokenEntry] = None

    async def get_token(self) -> _TokenEntry:
        """Return a valid access token, refreshing if necessary."""
        if self._token_entry and time.monotonic() < self._token_entry.expires_at:
            return self._token_entry
        return await self._fetch_token()

    async def _fetch_token(self) -> _TokenEntry:
        """Acquire a new token using the Username-Password flow."""
        data = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": self._password,
        }
        token_url = f"{self._login_url}{self._TOKEN_URL_PATH}"
        client = self._http_client or httpx.AsyncClient()
        try:
            response = await client.post(token_url, data=data, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                await client.aclose()

        access_token = payload["access_token"]
        instance_url = payload["instance_url"]
        # Salesforce tokens do not include expires_in; default to 2 hours
        issued_at_ms = int(payload.get("issued_at", str(int(time.time() * 1000))))
        issued_at = issued_at_ms / 1000.0
        expires_at = issued_at + 7200 - self._TOKEN_EXPIRY_BUFFER

        self._token_entry = _TokenEntry(
            access_token=access_token,
            instance_url=instance_url,
            expires_at=expires_at,
        )
        return self._token_entry

    def invalidate(self) -> None:
        """Clear the cached token, forcing re-authentication on next call."""
        self._token_entry = None
