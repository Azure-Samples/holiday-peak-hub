"""Adobe IMS JWT Service Account authentication for Adobe Experience Platform.

Handles token acquisition, caching, and automatic refresh using the
OAuth 2.0 JWT Bearer flow defined at:
https://developer.adobe.com/developer-console/docs/guides/authentication/JWT/
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

_TOKEN_EXPIRY_BUFFER_SECONDS = 60


@dataclass
class AdobeImsToken:
    """Holds a cached IMS access token with its expiry time."""

    access_token: str
    expires_at: float = field(default=0.0)

    def is_valid(self) -> bool:
        """Return True if the token is still usable."""
        return time.monotonic() < self.expires_at - _TOKEN_EXPIRY_BUFFER_SECONDS


class AdobeImsAuth:
    """Adobe IMS OAuth 2.0 client-credentials token provider.

    Credentials are read from environment variables:

    - ``AEP_CLIENT_ID``    – Adobe Developer Console client ID
    - ``AEP_CLIENT_SECRET``– Adobe Developer Console client secret
    - ``AEP_ORG_ID``       – Adobe IMS organisation ID (``@AdobeOrg`` suffix)
    - ``AEP_IMS_URL``      – IMS token endpoint base URL
                             (default: ``https://ims-na1.adobelogin.com``)

    All values can be overridden by passing keyword arguments to the
    constructor.
    """

    _DEFAULT_IMS_URL = "https://ims-na1.adobelogin.com"
    _TOKEN_PATH = "/ims/token/v3"
    _SCOPES = (
        "openid,AdobeID,read_organizations,additional_info.projectedProductContext,"
        "read_pc,ff_apis"
    )

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        org_id: Optional[str] = None,
        ims_url: Optional[str] = None,
    ) -> None:
        self._client_id = client_id or os.environ.get("AEP_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("AEP_CLIENT_SECRET", "")
        self._org_id = org_id or os.environ.get("AEP_ORG_ID", "")
        self._ims_url = (ims_url or os.environ.get("AEP_IMS_URL", self._DEFAULT_IMS_URL)).rstrip(
            "/"
        )
        self._cached: Optional[AdobeImsToken] = None

    async def get_token(self) -> str:
        """Return a valid Bearer token, refreshing if necessary."""
        if self._cached is not None and self._cached.is_valid():
            return self._cached.access_token
        return await self._fetch_token()

    async def _fetch_token(self) -> str:
        """Obtain a new access token from Adobe IMS."""
        url = f"{self._ims_url}{self._TOKEN_PATH}"
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": self._SCOPES,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            payload = response.json()

        access_token: str = payload["access_token"]
        expires_in: int = int(payload.get("expires_in", 3600))
        self._cached = AdobeImsToken(
            access_token=access_token,
            expires_at=time.monotonic() + expires_in,
        )
        return access_token

    @property
    def client_id(self) -> str:
        """Return the configured client ID."""
        return self._client_id

    def invalidate(self) -> None:
        """Clear the cached token, forcing a refresh on the next call."""
        self._cached = None
