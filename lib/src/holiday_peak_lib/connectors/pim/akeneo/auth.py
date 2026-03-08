"""OAuth 2.0 password-grant authentication handler for Akeneo PIM.

Akeneo uses an OAuth 2.0 *password* grant flow.  Access tokens expire after
one hour; this handler caches the token and refreshes it automatically.
"""

from __future__ import annotations

import os
import time

import httpx


class AkeneoAuth:  # pylint: disable=too-many-instance-attributes
    """Manages OAuth 2.0 token acquisition and caching for Akeneo.

    Credentials are sourced from the following environment variables when
    not provided at construction time:

    - ``AKENEO_BASE_URL``   — Akeneo instance URL
    - ``AKENEO_CLIENT_ID``  — OAuth client ID
    - ``AKENEO_CLIENT_SECRET`` — OAuth client secret
    - ``AKENEO_USERNAME``   — Akeneo user login
    - ``AKENEO_PASSWORD``   — Akeneo user password

    >>> import os
    >>> os.environ.update({
    ...     "AKENEO_BASE_URL": "https://demo.akeneo.com",
    ...     "AKENEO_CLIENT_ID": "client",
    ...     "AKENEO_CLIENT_SECRET": "secret",
    ...     "AKENEO_USERNAME": "user",
    ...     "AKENEO_PASSWORD": "pass",
    ... })
    >>> auth = AkeneoAuth()
    >>> auth._client_id
    'client'
    """

    _TOKEN_BUFFER = 60  # seconds before expiry to refresh

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or os.environ.get("AKENEO_BASE_URL", "")).rstrip("/")
        self._client_id = client_id or os.environ.get("AKENEO_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("AKENEO_CLIENT_SECRET", "")
        self._username = username or os.environ.get("AKENEO_USERNAME", "")
        self._password = password or os.environ.get("AKENEO_PASSWORD", "")
        self._transport = transport
        # Token cache
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    async def get_headers(self) -> dict[str, str]:
        """Return authorisation headers, refreshing the token if needed."""
        if self._access_token is None or time.monotonic() >= self._expires_at:
            await self._refresh_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _refresh_token(self) -> None:
        """Request a new access token from Akeneo."""
        async with httpx.AsyncClient(
            base_url=self._base_url, transport=self._transport, timeout=15.0
        ) as client:
            response = await client.post(
                "/api/oauth/v1/token",
                json={
                    "grant_type": "password",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "username": self._username,
                    "password": self._password,
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
            self._expires_at = time.monotonic() + expires_in - self._TOKEN_BUFFER
