"""Unit tests for SalesforceAuth token acquisition and caching."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holiday_peak_lib.connectors.crm_loyalty.salesforce.auth import (
    SalesforceAuth,
    _TokenEntry,
)


_MOCK_TOKEN_RESPONSE = {
    "access_token": "test_access_token_abc123",
    "instance_url": "https://myorg.salesforce.com",
    "issued_at": str(int(time.time() * 1000)),
    "token_type": "Bearer",
    "scope": "full",
    "id": "https://login.salesforce.com/id/00Dxx0000001gEREAY/005xx000001SwiUAAS",
    "signature": "somesig",
}


def _make_auth(http_client=None) -> SalesforceAuth:
    return SalesforceAuth(
        client_id="test_client_id",
        client_secret="test_client_secret",
        username="user@example.com",
        password="Password1!securitytoken",
        http_client=http_client,
    )


class TestSalesforceAuthInit:
    def test_defaults_from_kwargs(self):
        auth = SalesforceAuth(
            client_id="cid",
            client_secret="csec",
            username="u@x.com",
            password="pw",
        )
        assert auth._client_id == "cid"
        assert auth._client_secret == "csec"
        assert auth._username == "u@x.com"
        assert auth._password == "pw"
        assert auth._login_url == "https://login.salesforce.com"
        assert auth._token_entry is None

    def test_defaults_from_env(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_CLIENT_ID", "env_cid")
        monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "env_csec")
        monkeypatch.setenv("SALESFORCE_USERNAME", "env_u@x.com")
        monkeypatch.setenv("SALESFORCE_PASSWORD", "env_pw")
        monkeypatch.setenv("SALESFORCE_LOGIN_URL", "https://test.salesforce.com")
        auth = SalesforceAuth()
        assert auth._client_id == "env_cid"
        assert auth._login_url == "https://test.salesforce.com"

    def test_custom_login_url_trailing_slash_stripped(self):
        auth = SalesforceAuth(login_url="https://test.salesforce.com/")
        assert auth._login_url == "https://test.salesforce.com"


class TestSalesforceAuthGetToken:
    @pytest.mark.asyncio
    async def test_fetches_new_token_when_none_cached(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _MOCK_TOKEN_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        auth = _make_auth(http_client=mock_client)
        token = await auth.get_token()

        assert token.access_token == "test_access_token_abc123"
        assert token.instance_url == "https://myorg.salesforce.com"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_cached_token_when_valid(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _MOCK_TOKEN_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        auth = _make_auth(http_client=mock_client)
        token1 = await auth.get_token()
        token2 = await auth.get_token()

        # Should only call the API once
        assert mock_client.post.call_count == 1
        assert token1 is token2

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _MOCK_TOKEN_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        auth = _make_auth(http_client=mock_client)
        # Pre-populate with an already-expired token
        auth._token_entry = _TokenEntry(
            access_token="old_token",
            instance_url="https://myorg.salesforce.com",
            expires_at=time.monotonic() - 1,
        )
        token = await auth.get_token()

        assert token.access_token == "test_access_token_abc123"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_params_use_password_grant(self):
        mock_response = MagicMock()
        mock_response.json.return_value = _MOCK_TOKEN_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        auth = _make_auth(http_client=mock_client)
        await auth.get_token()

        _, kwargs = mock_client.post.call_args
        form_data = kwargs.get("data", {})
        assert form_data["grant_type"] == "password"
        assert form_data["client_id"] == "test_client_id"
        assert form_data["username"] == "user@example.com"


class TestSalesforceAuthInvalidate:
    def test_invalidate_clears_token(self):
        auth = _make_auth()
        auth._token_entry = _TokenEntry(
            access_token="tok",
            instance_url="https://x.com",
            expires_at=time.monotonic() + 3600,
        )
        auth.invalidate()
        assert auth._token_entry is None
