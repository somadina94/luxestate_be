from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
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
from app.services.audit_log_service import AuditLogService

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
    db: db_dependency, admin: admin_dependency, request: SubscriptionPlanCreate, http_req: Request
):
    plan = SellerSubscriptionService(db).create_subscription_plan(request)
    AuditLogService().create_log(
        db=db,
        action="subscription_plan.create",
        resource_type="subscription_plan",
        resource_id=getattr(plan, "id", None),
        user_id=admin.get("id"),
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return plan


@router.get(
    "/", response_model=List[SubscriptionPlanResponse], status_code=status.HTTP_200_OK
)
def get_all_subscription_plans(db: db_dependency, user: user_dependency, http_req: Request):
    rows = SellerSubscriptionService(db).get_subscription_plans()
    AuditLogService().create_log(
        db=db,
        action="subscription_plan.list",
        resource_type="subscription_plan",
        resource_id=None,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return rows


@router.get(
    "/{subscription_plan_id}",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_200_OK,
)
def get_subscription_plan(
    db: db_dependency, user: user_dependency, subscription_plan_id: int, http_req: Request
):
    row = SellerSubscriptionService(db).get_subscription_plan(subscription_plan_id)
    AuditLogService().create_log(
        db=db,
        action="subscription_plan.get",
        resource_type="subscription_plan",
        resource_id=subscription_plan_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return row


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
    http_req: Request,
):
    plan = SellerSubscriptionService(db).update_subscription_plan(
        subscription_plan_id, request
    )
    AuditLogService().create_log(
        db=db,
        action="subscription_plan.update",
        resource_type="subscription_plan",
        resource_id=subscription_plan_id,
        user_id=user.get("id"),
        changes=request.dict(exclude_unset=True),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return plan


@router.delete("/{subscription_plan_id}", status_code=status.HTTP_200_OK)
def delete_subscription_plan(
    db: db_dependency, user: user_dependency, subscription_plan_id: int, http_req: Request
):
    result = SellerSubscriptionService(db).delete_subscription_plan(subscription_plan_id)
    AuditLogService().create_log(
        db=db,
        action="subscription_plan.delete",
        resource_type="subscription_plan",
        resource_id=subscription_plan_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return result
