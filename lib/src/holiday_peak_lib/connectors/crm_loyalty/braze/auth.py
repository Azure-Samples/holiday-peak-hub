"""Braze API key authentication handler.

Manages Bearer token injection for every outgoing Braze REST request.
Credentials are read exclusively from environment variables and never
stored in source code.
"""

from __future__ import annotations

import os


class BrazeAuth:
    """Holds the Braze REST API key and provides the Authorization header.

    The API key is read from the ``BRAZE_API_KEY`` environment variable.

    >>> auth = BrazeAuth(api_key="test-key")
    >>> auth.headers["Authorization"]
    'Bearer test-key'
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key: str = api_key or os.environ.get("BRAZE_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "Braze API key is required. Set the BRAZE_API_KEY environment variable."
            )

    @property
    def headers(self) -> dict[str, str]:
        """Return HTTP headers required for authenticated Braze requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
