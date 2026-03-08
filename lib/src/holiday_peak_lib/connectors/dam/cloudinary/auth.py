"""Authentication helpers for the Cloudinary REST API.

Cloudinary uses an API key + API secret pair.  Signed requests include a
SHA-256 ``signature`` computed over the request parameters.  Unsigned requests
use the API key directly.

References:
    https://cloudinary.com/documentation/authentication
"""

from __future__ import annotations

import hashlib
import os
import time


class CloudinaryAuth:
    """Provides Cloudinary API credentials and request signing.

    Credentials are resolved from ``CLOUDINARY_API_KEY``,
    ``CLOUDINARY_API_SECRET``, and ``CLOUDINARY_CLOUD_NAME`` environment
    variables when not supplied at construction time.

    >>> auth = CloudinaryAuth(cloud_name="demo", api_key="key", api_secret="secret")
    >>> auth.cloud_name
    'demo'
    >>> auth.api_key
    'key'
    """

    def __init__(
        self,
        *,
        cloud_name: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.cloud_name = cloud_name or os.environ.get("CLOUDINARY_CLOUD_NAME", "")
        self.api_key = api_key or os.environ.get("CLOUDINARY_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("CLOUDINARY_API_SECRET", "")
        if not self.cloud_name or not self.api_key or not self._api_secret:
            raise ValueError(
                "Cloudinary credentials are required. "
                "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, "
                "and CLOUDINARY_API_SECRET env vars."
            )

    @property
    def api_secret(self) -> str:
        """Return the API secret (used internally by connectors)."""
        return self._api_secret

    def sign_params(self, params: dict) -> dict:
        """Return *params* extended with ``api_key``, ``timestamp``, and ``signature``.

        The signature is a SHA-256 hash of the sorted parameter string appended
        with the API secret.

        >>> auth = CloudinaryAuth(cloud_name="demo", api_key="key", api_secret="secret")
        >>> signed = auth.sign_params({"public_id": "sample"})
        >>> "signature" in signed and "timestamp" in signed
        True
        """
        ts = int(time.time())
        to_sign = {**params, "timestamp": ts}
        param_str = "&".join(f"{k}={v}" for k, v in sorted(to_sign.items()) if k != "api_key")
        signature = hashlib.sha256(f"{param_str}{self._api_secret}".encode()).hexdigest()
        return {**to_sign, "api_key": self.api_key, "signature": signature}
