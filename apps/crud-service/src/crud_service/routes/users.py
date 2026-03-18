"""User routes."""

from crud_service.auth import User, get_current_user
from crud_service.integrations import get_agent_client, get_event_publisher
from crud_service.repositories import UserRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()
user_repo = UserRepository()
agent_client = get_agent_client()
event_publisher = get_event_publisher()


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
    await event_publisher.publish(
        "user-events",
        "UserUpdated",
        {
            "id": updated.get("id"),
            "user_id": updated.get("id"),
            "entra_id": updated.get("entra_id"),
            "email": updated.get("email"),
            "name": updated.get("name"),
            "phone": updated.get("phone"),
            "timestamp": updated.get("updated_at") or updated.get("created_at"),
        },
    )
    return UserProfileResponse(**updated)


class CrmProfileResponse(BaseModel):
    """Enriched CRM profile."""

    user_id: str
    crm_profile: dict | None = None
    personalization: dict | None = None


@router.get("/users/me/crm", response_model=CrmProfileResponse)
async def get_crm_profile(current_user: User = Depends(get_current_user)):
    """Get the enriched CRM profile and personalization for the current user."""
    crm_profile = await agent_client.get_customer_profile(current_user.user_id)
    personalization = await agent_client.get_personalization(current_user.user_id)
    return CrmProfileResponse(
        user_id=current_user.user_id,
        crm_profile=crm_profile,
        personalization=personalization,
    )
