from enum import Enum
from typing import Annotated, Callable

from fastapi import Depends, HTTPException
from starlette import status
from sqlalchemy.orm import Session
from app.services.subscription import SubscriptionService

from app.database import SessionLocal
from app.models.subscription import SubscriptionStatus
from app.services.auth_service import get_current_user


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


class Permission(str, Enum):
    READ_PROPERTIES = "read:properties"
    CREATE_PROPERTIES = "create:properties"
    UPDATE_PROPERTIES = "update:properties"
    DELETE_PROPERTIES = "delete:properties"
    MANAGE_USERS = "manage:users"
    VIEW_ANALYTICS = "view:analytics"
    MANAGE_TICKETS = "manage:tickets"
    MANAGE_SUBSCRIPTIONS = "manage:subscriptions"
    MANAGE_ANNOUNCEMENTS = "manage:announcements"


# Map role strings (as embedded in JWT) to allowed permissions
ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "buyer": [Permission.READ_PROPERTIES],
    "seller": [
        Permission.READ_PROPERTIES,
        Permission.CREATE_PROPERTIES,
        Permission.UPDATE_PROPERTIES,
        Permission.DELETE_PROPERTIES,
    ],
    "admin": [
        Permission.READ_PROPERTIES,
        Permission.CREATE_PROPERTIES,
        Permission.UPDATE_PROPERTIES,
        Permission.DELETE_PROPERTIES,
        Permission.MANAGE_USERS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_TICKETS,
        Permission.MANAGE_SUBSCRIPTIONS,
        Permission.MANAGE_ANNOUNCEMENTS,
    ],
}


def require_permission(required: Permission) -> Callable[..., dict]:
    def dependency(current_user: CurrentUser) -> dict:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not autheticate user",
            )

        role = current_user.get("role")
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not authenticate user",
            )

        allowed = ROLE_PERMISSIONS.get(role, [])
        if required not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return dependency


def require_subscription(required: SubscriptionStatus) -> Callable[..., dict]:
    def dependency(db: db_dependency, current_user: CurrentUser) -> dict:
        subscription = SubscriptionService(db).get_user_active_subscription(
            current_user.get("id")
        )
        if not subscription or subscription.status != required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency
