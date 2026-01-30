"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crud_service.auth import User, get_current_user
from crud_service.repositories import UserRepository

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
    
    Returns authenticated user information from JWT token.
    """
    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        roles=current_user.roles,
    )


@router.post("/register")
async def register_user():
    """
    Register new user.
    
    TODO: Implement user registration flow with Entra ID B2C.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User registration not yet implemented",
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user.
    
    TODO: Implement token revocation if needed.
    """
    return {"message": "Logged out successfully"}
