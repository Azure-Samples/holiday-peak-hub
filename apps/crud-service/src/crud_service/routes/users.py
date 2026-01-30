"""User routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crud_service.auth import User, get_current_user
from crud_service.repositories import UserRepository

router = APIRouter()
user_repo = UserRepository()


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    name: str
    phone: str | None = None
    created_at: str


class UpdateProfileRequest(BaseModel):
    """Update profile request."""

    name: str | None = None
    phone: str | None = None


@router.get("/users/me", response_model=UserProfileResponse)
async def get_my_full_profile(current_user: User = Depends(get_current_user)):
    """Get full user profile from database."""
    user = await user_repo.get_by_entra_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
    return UserProfileResponse(**user)


@router.patch("/users/me", response_model=UserProfileResponse)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
):
    """Update user profile."""
    user = await user_repo.get_by_entra_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    if request.name:
        user["name"] = request.name
    if request.phone:
        user["phone"] = request.phone

    updated = await user_repo.update(user)
    return UserProfileResponse(**updated)
