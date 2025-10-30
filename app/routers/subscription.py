from fastapi import APIRouter, Depends, status, Request
from typing import Annotated
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.services.auth_service import get_current_user
from app.services.subscription import SubscriptionService
from app.dependencies import require_permission, Permission
from app.services.audit_log_service import AuditLogService


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
    http_req: Request,
):
    rows = SubscriptionService(db).get_subscriptions()
    AuditLogService().create_log(
        db=db,
        action="subscription.list_all",
        resource_type="subscription",
        resource_id=None,
        user_id=admin.get("id"),
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
    "/user/all",
    status_code=status.HTTP_200_OK,
    description="Get all subscriptions for a user",
)
def get_user_subscriptions(
    db: db_dependency,
    user: user_dependency,
    http_req: Request,
):
    rows = SubscriptionService(db).get_user_subscriptions(user.get("id"))
    AuditLogService().create_log(
        db=db,
        action="subscription.list_user",
        resource_type="subscription",
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
    "/user/active",
    status_code=status.HTTP_200_OK,
    description="Get the active subscription for a user",
)
def get_user_active_subscription(
    db: db_dependency,
    user: user_dependency,
    http_req: Request,
):
    row = SubscriptionService(db).get_user_active_subscription(user.get("id"))
    AuditLogService().create_log(
        db=db,
        action="subscription.user_active",
        resource_type="subscription",
        resource_id=getattr(row, "id", None) if row else None,
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
