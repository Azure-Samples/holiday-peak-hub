"""Authentication routes (Entra ID only)."""

from crud_service.auth import User, get_current_user
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()


class UserProfile(BaseModel):
    """User profile response."""

    user_id: str
    email: str
    name: str
    roles: list[str]


@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile.

    Returns authenticated user information extracted from the
    Entra ID JWT token (signature verified against JWKS).
    """
    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        roles=current_user.roles,
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user.

    Server-side: acknowledge logout.  Actual session invalidation
    happens on the client via MSAL ``logoutPopup()``.
    """
    return {"message": "Logged out successfully"}
