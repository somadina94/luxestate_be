from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.auth_service import get_current_user
from app.services.seller_subscription import SellerSubscriptionService
from app.schemas.seller_subscription import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanResponse,
)
from app.dependencies import require_permission, Permission

router = APIRouter(prefix="/seller_subscription", tags=["seller_subscription"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
admin_dependency = Annotated[
    dict, Depends(require_permission(Permission.MANAGE_SUBSCRIPTIONS))
]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_subscription_plan(
    db: db_dependency, admin: admin_dependency, request: SubscriptionPlanCreate
):
    return SellerSubscriptionService(db).create_subscription_plan(request)


@router.get(
    "/", response_model=List[SubscriptionPlanResponse], status_code=status.HTTP_200_OK
)
def get_all_subscription_plans(db: db_dependency, user: user_dependency):
    return SellerSubscriptionService(db).get_subscription_plans()


@router.get(
    "/{subscription_plan_id}",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_200_OK,
)
def get_subscription_plan(
    db: db_dependency, user: user_dependency, subscription_plan_id: int
):
    return SellerSubscriptionService(db).get_subscription_plan(subscription_plan_id)


@router.patch(
    "/{subscription_plan_id}",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_200_OK,
)
def update_subscription_plan(
    db: db_dependency,
    user: user_dependency,
    subscription_plan_id: int,
    request: SubscriptionPlanUpdate,
):
    return SellerSubscriptionService(db).update_subscription_plan(
        subscription_plan_id, request
    )


@router.delete("/{subscription_plan_id}", status_code=status.HTTP_200_OK)
def delete_subscription_plan(
    db: db_dependency, user: user_dependency, subscription_plan_id: int
):
    return SellerSubscriptionService(db).delete_subscription_plan(subscription_plan_id)
