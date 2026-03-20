"""Authentication dependencies using Microsoft Entra ID."""

import logging
import time
from typing import Annotated

import httpx
from crud_service.config import get_settings
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
_DEV_MOCK_AUTH_HEADER = "x-dev-auth-mock"
_DEV_MOCK_ROLES_HEADER = "x-dev-auth-roles"
_DEV_MOCK_USER_ID_HEADER = "x-dev-auth-user-id"
_DEV_MOCK_EMAIL_HEADER = "x-dev-auth-email"
_DEV_MOCK_NAME_HEADER = "x-dev-auth-name"
_ALLOWED_MOCK_ROLES = {"customer", "staff", "admin"}


class User(BaseModel):
    """Authenticated user information."""

    user_id: str
    email: str
    name: str
    roles: list[str]


class JWTConfig:
    """JWT configuration for Entra ID token validation with JWKS caching."""

    _JWKS_TTL = 3600  # Re-fetch keys every hour

    def __init__(self):
        self.tenant_id = settings.entra_tenant_id
        self.client_id = settings.entra_client_id
        self.issuer = settings.entra_issuer
        self._jwks_cache: dict | None = None
        self._jwks_fetched_at: float = 0.0

    @property
    def jwks_uri(self) -> str:
        """JWKS URI for token validation."""
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    async def get_signing_keys(self) -> dict:
        """
        Fetch and cache the JWKS key set from Entra ID.

        Keys are cached for ``_JWKS_TTL`` seconds.  A stale cache is
        returned if the remote fetch fails so the service degrades
        gracefully instead of blocking all requests.
        """
        now = time.monotonic()
        if self._jwks_cache and (now - self._jwks_fetched_at) < self._JWKS_TTL:
            return self._jwks_cache

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.jwks_uri)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_fetched_at = now
                logger.info("Refreshed JWKS from %s", self.jwks_uri)
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.HTTPStatusError,
            ValueError,
        ) as exc:
            if self._jwks_cache:
                logger.warning(
                    "JWKS refresh failed; using cached keys",
                    extra={"jwks_uri": self.jwks_uri, "error_type": type(exc).__name__},
                    exc_info=True,
                )
            else:
                logger.error(
                    "JWKS fetch failed and no cached keys available",
                    extra={"jwks_uri": self.jwks_uri, "error_type": type(exc).__name__},
                    exc_info=True,
                )
                raise

        return self._jwks_cache


jwt_config = JWTConfig()


def _is_dev_mock_auth_enabled() -> bool:
    return settings.is_development and settings.dev_auth_mock


def _build_dev_mock_user(request: Request) -> User | None:
    if not _is_dev_mock_auth_enabled():
        return None

    enabled_header = request.headers.get(_DEV_MOCK_AUTH_HEADER, "").strip().lower()
    if enabled_header != "true":
        return None

    raw_roles = request.headers.get(_DEV_MOCK_ROLES_HEADER, "")
    roles = [role.strip().lower() for role in raw_roles.split(",") if role.strip()]
    normalized_roles = [role for role in roles if role in _ALLOWED_MOCK_ROLES]

    if not normalized_roles:
        return None

    user_id = (
        request.headers.get(_DEV_MOCK_USER_ID_HEADER, "").strip() or f"mock-{normalized_roles[0]}"
    )
    email = request.headers.get(_DEV_MOCK_EMAIL_HEADER, "").strip() or f"{user_id}@local.dev"
    name = request.headers.get(_DEV_MOCK_NAME_HEADER, "").strip() or "Mock User"

    return User(
        user_id=user_id,
        email=email,
        name=name,
        roles=normalized_roles,
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(optional_security),
    ] = None,
) -> User:
    """
    Extract and validate JWT token from Authorization header.

    Validates token signature against Entra ID JWKS endpoint,
    checks issuer, audience, and expiry claims.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    if credentials is None:
        mock_user = _build_dev_mock_user(request)
        if mock_user is not None:
            return mock_user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Fetch signing keys
        jwks = await jwt_config.get_signing_keys()

        # Determine the correct key by matching the ``kid`` header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        rsa_key: dict = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key.get("use", "sig"),
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate signing key",
            )

        # Fully verify the token (signature + exp + iss + aud)
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=jwt_config.client_id,
            issuer=jwt_config.issuer,
            options={
                "verify_aud": bool(jwt_config.client_id),
                "verify_iss": bool(jwt_config.issuer),
                "verify_exp": True,
            },
        )

        user_id = payload.get("sub") or payload.get("oid")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user identifier",
            )

        email = payload.get("email") or payload.get("preferred_username")
        name = payload.get("name", "Unknown User")
        roles = payload.get("roles", [])

        return User(user_id=user_id, email=email, name=name, roles=roles)

    except JWTError as e:
        logger.error("JWT validation error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, ValueError) as exc:
        logger.error(
            "Authentication dependency unavailable",
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable",
        ) from exc


def require_role(required_role: str):
    """
    Dependency to check if user has required role.

    Usage:
        @app.get("/admin")
        async def admin_route(user: User = Depends(require_role("admin"))):
            ...
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user

    return role_checker


# Common role dependencies
require_customer = require_role("customer")
require_staff = require_role("staff")
require_admin = require_role("admin")


# Optional authentication (for endpoints that work for both anonymous and authenticated)
async def get_current_user_optional(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(optional_security),
    ] = None,
) -> User | None:
    """Get current user if authenticated, otherwise return None."""
    try:
        return await get_current_user(request, credentials)
    except HTTPException as exc:
        if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            if credentials is not None:
                logger.warning(
                    "Optional auth rejected provided credentials; continuing anonymously",
                    extra={"status_code": exc.status_code},
                    exc_info=True,
                )
            return None
        logger.error(
            "Optional auth service failure",
            extra={"status_code": exc.status_code},
            exc_info=True,
        )
        raise


async def get_key_vault_secret(secret_name: str) -> str:
    """Read a secret value from Key Vault using managed identity credentials."""
    from azure.identity.aio import DefaultAzureCredential
    from azure.keyvault.secrets.aio import SecretClient

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=settings.key_vault_uri, credential=credential)
    try:
        secret = await client.get_secret(secret_name)
        return secret.value
    finally:
        await client.close()
        await credential.close()
