"""OAuth 2.0 JWT Bearer authentication handler for Oracle Fusion Cloud SCM.

Oracle Fusion Cloud uses OAuth 2.0 with the JWT Bearer grant type. This module
handles token acquisition, in-memory caching with TTL-based expiry, and
automatic refresh so connector code never needs to manage credentials directly.

Configuration via environment variables:
    ORACLE_SCM_BASE_URL      — Instance base URL, e.g. https://<host>
    ORACLE_SCM_TOKEN_URL     — Token endpoint URL
    ORACLE_SCM_CLIENT_ID     — OAuth 2.0 client ID
    ORACLE_SCM_CLIENT_SECRET — OAuth 2.0 client secret
    ORACLE_SCM_SCOPE         — Space-separated OAuth scopes (optional)
"""

import os
import time
from typing import Optional

import httpx


class OracleSCMAuthError(Exception):
    """Raised when Oracle SCM authentication fails."""


class OracleSCMAuth:
    """OAuth 2.0 Client Credentials token manager for Oracle Fusion Cloud SCM.

    Tokens are cached in memory until they expire (with a safety buffer).
    Call :meth:`get_token` before every request; it returns a cached token if
    still valid, or fetches a new one automatically.

    >>> import asyncio
    >>> auth = OracleSCMAuth(
    ...     token_url="https://oracle.example.com/oauth/token",
    ...     client_id="client123",
    ...     client_secret="secret",
    ...     scope="SCM",
    ... )
    >>> auth._token is None
    True
    """

    _EXPIRY_BUFFER_SECONDS = 60

    def __init__(
        self,
        token_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None,
        http_timeout: float = 10.0,
    ) -> None:
        self._token_url = token_url or os.environ.get("ORACLE_SCM_TOKEN_URL", "")
        self._client_id = client_id or os.environ.get("ORACLE_SCM_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("ORACLE_SCM_CLIENT_SECRET", "")
        self._scope = scope or os.environ.get("ORACLE_SCM_SCOPE", "")
        self._http_timeout = http_timeout

        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def _is_token_valid(self) -> bool:
        """Return True if the cached token is still valid."""
        return self._token is not None and time.monotonic() < self._expires_at

    async def get_token(self) -> str:
        """Return a valid bearer token, refreshing if necessary.

        Raises :class:`OracleSCMAuthError` when the token request fails.
        """
        if self._is_token_valid():
            return self._token  # type: ignore[return-value]
        return await self._fetch_token()

    async def _fetch_token(self) -> str:
        """Request a new access token from the Oracle token endpoint."""
        if not self._token_url:
            raise OracleSCMAuthError("ORACLE_SCM_TOKEN_URL is not configured.")
        if not self._client_id or not self._client_secret:
            raise OracleSCMAuthError(
                "ORACLE_SCM_CLIENT_ID and ORACLE_SCM_CLIENT_SECRET must be set."
            )

        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scope:
            data["scope"] = self._scope

        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            try:
                response = await client.post(self._token_url, data=data)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OracleSCMAuthError(
                    f"Token request failed with status {exc.response.status_code}: "
                    f"{exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise OracleSCMAuthError(f"Token request network error: {exc}") from exc

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise OracleSCMAuthError(f"No access_token in Oracle token response: {payload}")

        expires_in = int(payload.get("expires_in", 3600))
        self._token = token
        self._expires_at = time.monotonic() + expires_in - self._EXPIRY_BUFFER_SECONDS
        return self._token

    def invalidate(self) -> None:
        """Force the next :meth:`get_token` call to fetch a fresh token."""
        self._token = None
        self._expires_at = 0.0
