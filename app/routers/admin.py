from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status
from app.database import SessionLocal
from app.models.user import User
from typing import Annotated, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.dependencies import db_dependency, require_permission, Permission
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import get_current_user
from app.schemas.user import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(require_permission(Permission.MANAGE_USERS))]
admin_dependency = Annotated[dict, Depends(require_permission(Permission.MANAGE_USERS))]
current_user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
def get_all_users(user: user_dependency, db: db_dependency, http_req: Request):
    rows = db.query(User).all()
    AuditLogService().create_log(
        db=db,
        action="user.list",
        resource_type="user",
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


@router.patch("/suspend/{user_id}", status_code=status.HTTP_200_OK)
async def suspend_user(
    db: db_dependency, user: user_dependency, user_id: int, http_req: Request
):
    user_to_suspend: User = db.query(User).filter(User.id == user_id).first()
    if not user_to_suspend:
        AuditLogService().create_log(
            db=db,
            action="user.suspend",
            resource_type="user",
            resource_id=user_id,
            user_id=user.get("id"),
            status="failure",
            status_code=status.HTTP_404_NOT_FOUND,
            error_message="user_not_found",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_to_suspend.is_active = False
    db.commit()
    db.refresh(user_to_suspend)
    AuditLogService().create_log(
        db=db,
        action="user.suspend",
        resource_type="user",
        resource_id=user_to_suspend.id,
        user_id=user.get("id"),
        changes={"is_active": {"old": True, "new": False}},
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"message": "User suspended successfully"}


@router.patch("/unsuspend/{user_id}", status_code=status.HTTP_200_OK)
async def unsuspend_user(
    db: db_dependency, user: user_dependency, user_id: int, http_req: Request
):
    user_to_unsuspend: User = db.query(User).filter(User.id == user_id).first()
    if not user_to_unsuspend:
        AuditLogService().create_log(
            db=db,
            action="user.unsuspend",
            resource_type="user",
            resource_id=user_id,
            user_id=user.get("id"),
            status="failure",
            status_code=status.HTTP_404_NOT_FOUND,
            error_message="user_not_found",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_to_unsuspend.is_active = True
    db.commit()
    db.refresh(user_to_unsuspend)
    AuditLogService().create_log(
        db=db,
        action="user.unsuspend",
        resource_type="user",
        resource_id=user_to_unsuspend.id,
        user_id=user.get("id"),
        changes={"is_active": {"old": False, "new": True}},
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"message": "User unsuspended successfully"}


# Audit Logs
@router.get("/audit-logs", status_code=status.HTTP_200_OK)
def get_audit_logs(
    db: db_dependency,
    admin: admin_dependency,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    skip: int = 0,
):
    """Get audit logs with filtering (admin only)"""
    return AuditLogService().get_logs(
        db=db,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        skip=skip,
    )


@router.get("/audit-logs/user/{user_id}", status_code=status.HTTP_200_OK)
def get_user_audit_logs(
    db: db_dependency,
    admin: admin_dependency,
    user_id: int,
    days: int = 30,
):
    """Get audit logs for a specific user (admin only)"""
    return AuditLogService().get_user_activity(db=db, user_id=user_id, days=days)


@router.get(
    "/audit-logs/resource/{resource_type}/{resource_id}", status_code=status.HTTP_200_OK
)
def get_resource_audit_logs(
    db: db_dependency,
    admin: admin_dependency,
    resource_type: str,
    resource_id: int,
):
    """Get complete history for a resource (admin only)"""
    return AuditLogService().get_resource_history(
        db=db, resource_type=resource_type, resource_id=resource_id
    )


@router.get("/audit-logs/security", status_code=status.HTTP_200_OK)
def get_security_audit_logs(
    db: db_dependency,
    admin: admin_dependency,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get security-related audit logs (failed logins, unauthorized access, etc.)"""
    return AuditLogService().get_logs(
        db=db,
        action=None,  # fetch by action prefix using resource_type or filter client-side
        resource_type="auth",  # include http as well if desired
        start_date=start_date,
        end_date=end_date,
        limit=200,
        skip=0,
    )


@router.get("/users/audit-logs/me", status_code=status.HTTP_200_OK)
def get_my_audit_logs(
    db: db_dependency,
    user: current_user_dependency,
    days: int = 30,
):
    """Users can view their own audit logs (privacy/transparency)"""
    return AuditLogService().get_user_activity(db=db, user_id=user.get("id"), days=days)
