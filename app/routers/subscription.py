from fastapi import APIRouter, Depends, status
from typing import Annotated
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.services.auth_service import get_current_user
from app.services.subscription import SubscriptionService
from app.dependencies import require_permission, Permission


router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
admin_dependency = Annotated[
    dict, Depends(require_permission(Permission.MANAGE_SUBSCRIPTIONS))
]


@router.get("/", status_code=status.HTTP_200_OK, description="Get all subscriptions")
def get_subscriptions(
    db: db_dependency,
    admin: admin_dependency,
):
    return SubscriptionService(db).get_subscriptions()


@router.get(
    "/user/all",
    status_code=status.HTTP_200_OK,
    description="Get all subscriptions for a user",
)
def get_user_subscriptions(
    db: db_dependency,
    user: user_dependency,
):
    return SubscriptionService(db).get_user_subscriptions(user.get("id"))


@router.get(
    "/user/active",
    status_code=status.HTTP_200_OK,
    description="Get the active subscription for a user",
)
def get_user_active_subscription(
    db: db_dependency,
    user: user_dependency,
):
    return SubscriptionService(db).get_user_active_subscription(user.get("id"))
