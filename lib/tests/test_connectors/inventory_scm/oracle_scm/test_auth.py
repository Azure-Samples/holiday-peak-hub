"""Tests for OracleSCMAuth token management."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from holiday_peak_lib.connectors.inventory_scm.oracle_scm.auth import (
    OracleSCMAuth,
    OracleSCMAuthError,
)


class TestOracleSCMAuthInit:
    """Test OracleSCMAuth initialisation."""

    def test_defaults_from_env(self, monkeypatch):
        monkeypatch.setenv("ORACLE_SCM_TOKEN_URL", "https://oracle.example.com/token")
        monkeypatch.setenv("ORACLE_SCM_CLIENT_ID", "cid")
        monkeypatch.setenv("ORACLE_SCM_CLIENT_SECRET", "csec")
        monkeypatch.setenv("ORACLE_SCM_SCOPE", "SCM")
        auth = OracleSCMAuth()
        assert auth._token_url == "https://oracle.example.com/token"
        assert auth._client_id == "cid"
        assert auth._client_secret == "csec"
        assert auth._scope == "SCM"

    def test_explicit_params_override_env(self, monkeypatch):
        monkeypatch.setenv("ORACLE_SCM_CLIENT_ID", "env_cid")
        auth = OracleSCMAuth(
            token_url="https://t.example.com/token",
            client_id="explicit_cid",
            client_secret="sec",
        )
        assert auth._client_id == "explicit_cid"

    def test_token_initially_none(self):
        auth = OracleSCMAuth(token_url="u", client_id="c", client_secret="s")
        assert auth._token is None
        assert not auth._is_token_valid()


class TestOracleSCMAuthFetchToken:
    """Test token fetching and caching."""

    @pytest.fixture
    def auth(self):
        return OracleSCMAuth(
            token_url="https://oracle.example.com/token",
            client_id="client123",
            client_secret="secret",
            scope="SCM",
        )

    @pytest.fixture
    def mock_token_response(self):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"access_token": "tok-abc", "expires_in": 3600}
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.asyncio
    async def test_get_token_fetches_and_caches(self, auth, mock_token_response):
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(post=AsyncMock(return_value=mock_token_response))
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            token = await auth.get_token()

        assert token == "tok-abc"
        assert auth._token == "tok-abc"
        assert auth._is_token_valid()

    @pytest.mark.asyncio
    async def test_cached_token_returned_without_http_call(self, auth):
        auth._token = "cached-token"
        auth._expires_at = time.monotonic() + 3600
        token = await auth.get_token()
        assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_missing_token_url_raises(self):
        auth = OracleSCMAuth(token_url="", client_id="c", client_secret="s")
        with pytest.raises(OracleSCMAuthError, match="ORACLE_SCM_TOKEN_URL"):
            await auth.get_token()

    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self):
        auth = OracleSCMAuth(
            token_url="https://t.example.com/token", client_id="", client_secret=""
        )
        with pytest.raises(OracleSCMAuthError, match="CLIENT_ID"):
            await auth.get_token()

    @pytest.mark.asyncio
    async def test_http_status_error_raises(self, auth):
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 401
        error_resp.text = "Unauthorized"
        http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=error_resp)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(side_effect=http_error)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(OracleSCMAuthError, match="401"):
                await auth.get_token()

    @pytest.mark.asyncio
    async def test_network_error_raises(self, auth):
        req_error = httpx.RequestError("Connection refused", request=MagicMock())

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(side_effect=req_error)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(OracleSCMAuthError, match="network error"):
                await auth.get_token()

    @pytest.mark.asyncio
    async def test_response_missing_access_token_raises(self, auth):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"token_type": "Bearer"}
        resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(OracleSCMAuthError, match="access_token"):
                await auth.get_token()

    def test_invalidate_clears_token(self, auth):
        auth._token = "tok"
        auth._expires_at = time.monotonic() + 3600
        auth.invalidate()
        assert auth._token is None
        assert not auth._is_token_valid()
