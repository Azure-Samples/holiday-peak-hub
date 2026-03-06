"""Unit tests for JWT JWKS verification in auth dependencies."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import crud_service.auth.dependencies as deps_module
import httpx
import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

JWTConfig = deps_module.JWTConfig
get_current_user = deps_module.get_current_user
get_current_user_optional = deps_module.get_current_user_optional
User = deps_module.User


# ── JWTConfig JWKS caching ──────────────────────────────────────────


class TestJWTConfigJwks:
    """Tests for JWTConfig.get_signing_keys JWKS fetching & caching."""

    @pytest.mark.asyncio
    async def test_fetches_and_caches_keys(self, monkeypatch):
        """Should fetch JWKS and cache them."""
        fake_jwks = {"keys": [{"kid": "key-1", "kty": "RSA", "n": "abc", "e": "AQAB"}]}

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return fake_jwks

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, url):
                return FakeResponse()

        monkeypatch.setattr(deps_module.httpx, "AsyncClient", lambda **kw: FakeClient())

        config = JWTConfig()
        config.tenant_id = "test-tenant"

        result = await config.get_signing_keys()
        assert result == fake_jwks

        # Second call should use cache
        result2 = await config.get_signing_keys()
        assert result2 == fake_jwks

    @pytest.mark.asyncio
    async def test_uses_stale_cache_on_failure(self, monkeypatch):
        """Should return stale cache when JWKS refresh fails."""
        config = JWTConfig()
        config.tenant_id = "test-tenant"
        config._jwks_cache = {"keys": [{"kid": "old-key"}]}
        config._jwks_fetched_at = 0  # expired

        class FailingClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, url):
                raise httpx.ConnectError("network down")

        monkeypatch.setattr(deps_module.httpx, "AsyncClient", lambda **kw: FailingClient())

        result = await config.get_signing_keys()
        assert result["keys"][0]["kid"] == "old-key"

    @pytest.mark.asyncio
    async def test_raises_when_no_cache_and_fetch_fails(self, monkeypatch):
        """Should raise when fetch fails and no cache is available."""
        config = JWTConfig()
        config.tenant_id = "test-tenant"

        class FailingClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def get(self, url):
                raise httpx.ConnectError("network down")

        monkeypatch.setattr(deps_module.httpx, "AsyncClient", lambda **kw: FailingClient())

        with pytest.raises(httpx.ConnectError):
            await config.get_signing_keys()


# ── get_current_user ────────────────────────────────────────────────


class TestGetCurrentUser:
    """Tests for get_current_user JWT validation."""

    @pytest.mark.asyncio
    async def test_rejects_missing_kid(self, monkeypatch):
        """Should reject token when kid header doesn't match any JWKS key."""

        async def fake_keys():
            return {"keys": [{"kid": "other-key", "kty": "RSA", "n": "x", "e": "y"}]}

        monkeypatch.setattr(deps_module.jwt_config, "get_signing_keys", fake_keys)

        # Create a minimal token with a different kid
        token = jose_jwt.encode(
            {"sub": "user-1"},
            "secret",
            algorithm="HS256",
            headers={"kid": "unknown-key"},
        )

        creds = MagicMock()
        creds.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401
        assert "signing key" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_invalid_signature(self, monkeypatch):
        """Should reject token with invalid signature via JWTError."""
        from jose import JWTError

        async def fake_keys():
            return {
                "keys": [
                    {
                        "kid": "test-kid",
                        "kty": "RSA",
                        "n": "wLi3",
                        "e": "AQAB",
                        "use": "sig",
                    }
                ]
            }

        monkeypatch.setattr(deps_module.jwt_config, "get_signing_keys", fake_keys)

        # Forge a token with kid matching but invalid RSA signature
        token = jose_jwt.encode(
            {"sub": "user-1"},
            "wrong-secret",
            algorithm="HS256",
            headers={"kid": "test-kid"},
        )

        creds = MagicMock()
        creds.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_extracts_user_from_valid_token(self, monkeypatch):
        """Should return User when token is valid."""

        payload = {
            "sub": "user-1",
            "email": "a@b.com",
            "name": "Alice",
            "roles": ["customer"],
            "exp": int(time.time()) + 3600,
        }

        async def fake_keys():
            return {"keys": [{"kid": "k1", "kty": "RSA", "n": "x", "e": "AQAB"}]}

        monkeypatch.setattr(deps_module.jwt_config, "get_signing_keys", fake_keys)

        # Patch jwt.decode to bypass actual RSA verification for unit test
        monkeypatch.setattr(
            deps_module.jwt,
            "decode",
            lambda token, key, algorithms, audience, issuer, options: payload,
        )

        token = "fake.jwt.token"
        creds = MagicMock()
        creds.credentials = token

        # Also patch get_unverified_header to return matching kid
        monkeypatch.setattr(
            deps_module.jwt,
            "get_unverified_header",
            lambda t: {"kid": "k1", "alg": "RS256"},
        )

        user = await get_current_user(creds)
        assert isinstance(user, User)
        assert user.user_id == "user-1"
        assert user.email == "a@b.com"
        assert user.name == "Alice"
        assert "customer" in user.roles

    @pytest.mark.asyncio
    async def test_uses_oid_when_sub_missing(self, monkeypatch):
        """Should fall back to 'oid' claim when 'sub' is absent."""

        payload = {
            "oid": "oid-user-1",
            "preferred_username": "a@b.com",
            "name": "Bob",
            "roles": [],
        }

        async def fake_keys():
            return {"keys": [{"kid": "k1", "kty": "RSA", "n": "x", "e": "AQAB"}]}

        monkeypatch.setattr(deps_module.jwt_config, "get_signing_keys", fake_keys)
        monkeypatch.setattr(
            deps_module.jwt,
            "decode",
            lambda token, key, algorithms, audience, issuer, options: payload,
        )
        monkeypatch.setattr(
            deps_module.jwt,
            "get_unverified_header",
            lambda t: {"kid": "k1", "alg": "RS256"},
        )

        creds = MagicMock()
        creds.credentials = "fake.jwt.token"

        user = await get_current_user(creds)
        assert user.user_id == "oid-user-1"
        assert user.email == "a@b.com"

    @pytest.mark.asyncio
    async def test_rejects_token_without_user_id(self, monkeypatch):
        """Should reject tokens missing both sub and oid."""

        payload = {"email": "a@b.com", "name": "Nobody"}

        async def fake_keys():
            return {"keys": [{"kid": "k1", "kty": "RSA", "n": "x", "e": "AQAB"}]}

        monkeypatch.setattr(deps_module.jwt_config, "get_signing_keys", fake_keys)
        monkeypatch.setattr(
            deps_module.jwt,
            "decode",
            lambda token, key, algorithms, audience, issuer, options: payload,
        )
        monkeypatch.setattr(
            deps_module.jwt,
            "get_unverified_header",
            lambda t: {"kid": "k1", "alg": "RS256"},
        )

        creds = MagicMock()
        creds.credentials = "fake.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401
        assert "user identifier" in exc_info.value.detail.lower()


class TestGetCurrentUserOptional:
    """Tests for optional auth dependency behavior."""

    @pytest.mark.asyncio
    async def test_optional_auth_runtime_failure_returns_none(self, monkeypatch, caplog):
        """Unexpected runtime errors in optional auth should degrade to anonymous."""

        async def _boom(_credentials):
            raise RuntimeError("jwks runtime failure")

        monkeypatch.setattr(deps_module, "get_current_user", _boom)

        creds = MagicMock()
        creds.credentials = "fake.jwt.token"

        with caplog.at_level("WARNING"):
            user = await get_current_user_optional(creds)

        assert user is None
        assert "Optional auth runtime failure" in caplog.text
