"""Authentication package."""

from crud_service.auth.dependencies import (
    User,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_customer,
    require_role,
    require_staff,
)

__all__ = [
    "User",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_customer",
    "require_staff",
    "require_admin",
]
