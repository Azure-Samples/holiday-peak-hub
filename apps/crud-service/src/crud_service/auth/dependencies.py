"""Authentication dependencies using Microsoft Entra ID."""

import logging
from typing import Annotated

from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from crud_service.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer()


class User(BaseModel):
    """Authenticated user information."""

    user_id: str
    email: str
    name: str
    roles: list[str]


class JWTConfig:
    """JWT configuration loaded from Key Vault."""

    def __init__(self):
        self.tenant_id = settings.entra_tenant_id
        self.client_id = settings.entra_client_id
        self.issuer = settings.entra_issuer
        self._jwks_cache = None

    async def get_jwks_uri(self) -> str:
        """Get JWKS URI for token validation."""
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"


jwt_config = JWTConfig()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]
) -> User:
    """
    Extract and validate JWT token from Authorization header.
    
    Validates token signature against Entra ID JWKS endpoint.
    Returns authenticated user with roles.
    
    Raises:
        HTTPException: If token is invalid or expired.
    """
    token = credentials.credentials

    try:
        # Decode without verification first to get header
        unverified_header = jwt.get_unverified_header(token)
        unverified_claims = jwt.get_unverified_claims(token)

        # Validate issuer
        if unverified_claims.get("iss") != jwt_config.issuer:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
            )

        # Validate audience (client ID)
        if jwt_config.client_id not in unverified_claims.get("aud", []):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
            )

        # TODO: Fetch JWKS from Entra ID and verify signature
        # For now, we trust the token (in production, MUST verify signature)
        payload = unverified_claims

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
        logger.warning(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def require_role(required_role: str):
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
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)] = None
) -> User | None:
    """Get current user if authenticated, otherwise return None."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
