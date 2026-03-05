"""Unit tests for SAPS4HANAAuth."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.auth import SAPS4HANAAuth

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token_response(access_token: str = "tok-abc", expires_in: int = 3600) -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": access_token, "expires_in": expires_in, "token_type": "Bearer"},
    )


def _mock_transport(response: httpx.Response) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _req: response)


# ---------------------------------------------------------------------------
# API Key mode
# ---------------------------------------------------------------------------


class TestAPIKeyAuth:
    def test_returns_api_key_header(self):
        auth = SAPS4HANAAuth(api_key="MY-KEY")
        import asyncio

        headers = asyncio.run(auth.get_headers())
        assert headers == {"APIKey": "MY-KEY"}

    def test_api_key_takes_precedence_over_oauth(self):
        auth = SAPS4HANAAuth(
            api_key="MY-KEY",
            token_url="https://token.example.com",
            client_id="cid",
            client_secret="csec",
        )
        import asyncio

        headers = asyncio.run(auth.get_headers())
        assert "APIKey" in headers
        assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# OAuth 2.0 mode
# ---------------------------------------------------------------------------


class TestOAuth2Auth:
    def test_fetches_token_and_returns_bearer(self):
        transport = _mock_transport(_token_response("tok-xyz"))
        auth = SAPS4HANAAuth(
            token_url="https://token.example.com/oauth/token",
            client_id="cid",
            client_secret="csec",
            transport=transport,
        )
        import asyncio

        headers = asyncio.run(auth.get_headers())
        assert headers == {"Authorization": "Bearer tok-xyz"}

    def test_token_cached_on_second_call(self):
        transport = _mock_transport(_token_response("tok-abc"))
        auth = SAPS4HANAAuth(
            token_url="https://token.example.com/oauth/token",
            client_id="cid",
            client_secret="csec",
            transport=transport,
        )
        import asyncio

        asyncio.run(auth.get_headers())
        # Swap transport to one that would fail if called
        auth._transport = httpx.MockTransport(
            lambda _: httpx.Response(500, json={"error": "should-not-be-called"})
        )
        headers = asyncio.run(auth.get_headers())
        assert headers["Authorization"] == "Bearer tok-abc"

    def test_token_refreshed_when_expired(self):
        call_count = 0

        def handler(_req):
            nonlocal call_count
            call_count += 1
            return _token_response(f"tok-{call_count}", expires_in=1)

        transport = httpx.MockTransport(handler)
        auth = SAPS4HANAAuth(
            token_url="https://token.example.com/oauth/token",
            client_id="cid",
            client_secret="csec",
            transport=transport,
        )
        import asyncio

        asyncio.run(auth.get_headers())
        # Expire the token
        auth._token_expires_at = time.monotonic() - 1
        asyncio.run(auth.get_headers())
        assert call_count == 2

    def test_invalidate_forces_refresh(self):
        call_count = 0

        def handler(_req):
            nonlocal call_count
            call_count += 1
            return _token_response(f"tok-{call_count}")

        transport = httpx.MockTransport(handler)
        auth = SAPS4HANAAuth(
            token_url="https://token.example.com/oauth/token",
            client_id="cid",
            client_secret="csec",
            transport=transport,
        )
        import asyncio

        asyncio.run(auth.get_headers())
        auth.invalidate()
        asyncio.run(auth.get_headers())
        assert call_count == 2

    def test_raises_when_token_url_missing(self):
        auth = SAPS4HANAAuth(client_id="cid", client_secret="csec")
        import asyncio

        with pytest.raises(ValueError, match="SAP_S4HANA_TOKEN_URL"):
            asyncio.run(auth.get_headers())

    def test_raises_when_credentials_missing(self):
        auth = SAPS4HANAAuth(token_url="https://token.example.com")
        import asyncio

        with pytest.raises(ValueError, match="SAP_S4HANA_CLIENT_ID"):
            asyncio.run(auth.get_headers())

    def test_raises_on_http_error(self):
        transport = httpx.MockTransport(lambda _: httpx.Response(401, json={"error": "unauth"}))
        auth = SAPS4HANAAuth(
            token_url="https://token.example.com/oauth/token",
            client_id="cid",
            client_secret="csec",
            transport=transport,
        )
        import asyncio

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(auth.get_headers())

    def test_env_vars_are_read(self, monkeypatch):
        monkeypatch.setenv("SAP_S4HANA_API_KEY", "env-key")
        auth = SAPS4HANAAuth()
        import asyncio

        headers = asyncio.run(auth.get_headers())
        assert headers == {"APIKey": "env-key"}
        monkeypatch.delenv("SAP_S4HANA_API_KEY", raising=False)
