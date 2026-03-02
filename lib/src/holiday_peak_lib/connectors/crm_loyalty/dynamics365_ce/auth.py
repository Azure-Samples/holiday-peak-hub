"""Azure AD authentication for Dynamics 365 Customer Engagement.

Obtains bearer tokens using ``DefaultAzureCredential`` (supports managed
identity, environment credentials, CLI auth, etc.) and caches them until
they expire to minimise redundant token requests.
"""

from __future__ import annotations

import time
from typing import Optional


class _TokenCache:
    """Lightweight in-memory token cache."""

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def get(self) -> Optional[str]:
        if self._token and time.monotonic() < self._expires_at:
            return self._token
        return None

    def set(self, token: str, expires_in: float) -> None:
        # Refresh 60 s before real expiry to avoid clock-skew races.
        self._token = token
        self._expires_at = time.monotonic() + max(0.0, expires_in - 60.0)

    def clear(self) -> None:
        self._token = None
        self._expires_at = 0.0


class AzureADTokenProvider:
    """Provides Azure AD bearer tokens for a Dynamics 365 CE resource.

    :param resource_url: The Dynamics 365 instance URL used as the OAuth
        audience, e.g. ``https://org.crm.dynamics.com``.
    :param credential: An optional ``azure.identity`` credential instance.
        When *None*, a fresh ``DefaultAzureCredential`` is used.

    Example (no network I/O)::

        >>> provider = AzureADTokenProvider.__new__(AzureADTokenProvider)
        >>> provider._cache = _TokenCache()
        >>> provider._cache.set("tok", 3600)
        >>> provider._cache.get()
        'tok'
    """

    def __init__(self, resource_url: str, credential=None) -> None:
        self._resource_url = resource_url.rstrip("/")
        self._scope = f"{self._resource_url}/.default"
        self._cache = _TokenCache()

        if credential is not None:
            self._credential = credential
        else:
            # Lazy import so that azure-identity is only required at runtime.
            from azure.identity import DefaultAzureCredential  # noqa: PLC0415

            self._credential = DefaultAzureCredential()

    async def get_token(self) -> str:
        """Return a valid bearer token, refreshing if necessary.

        :returns: Raw access-token string.
        :raises RuntimeError: If token acquisition fails.
        """
        cached = self._cache.get()
        if cached is not None:
            return cached

        # azure-identity is synchronous; run in thread pool to stay async-safe.
        import asyncio  # noqa: PLC0415

        loop = asyncio.get_event_loop()
        token_obj = await loop.run_in_executor(
            None,
            lambda: self._credential.get_token(self._scope),
        )
        expires_in = max(0.0, token_obj.expires_on - time.time()) if token_obj.expires_on else 3600.0
        self._cache.set(token_obj.token, expires_in)
        return token_obj.token

    def invalidate(self) -> None:
        """Force the next call to ``get_token`` to re-acquire a fresh token."""
        self._cache.clear()
