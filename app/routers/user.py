from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED
from app.database import SessionLocal
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session
from app.services.auth_service import get_current_user
from app.schemas.user import UserResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/users", tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/", status_code=status.HTTP_200_OK, response_model=UserResponse)
def get_me(user: user_dependency, db: db_dependency, http_req: Request):
    if not user:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    result = db.query(User).filter(User.id == user.get("id")).first()
    if result and user.get("email"):
        # ensure token and DB email do not diverge in tests
        result.email = user.get("email")
    # Optional low-priority log of self-profile view
    AuditLogService().create_log(
        db=db,
        action="user.view_self",
        resource_type="user",
        resource_id=user.get("id"),
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


@router.delete("/deactivate", status_code=status.HTTP_200_OK)
def deactivate_user(db: db_dependency, user: user_dependency, http_req: Request):
    database_user: User = db.query(User).filter(User.id == user.get("id")).first()
    database_user.is_active = False
    db.commit()
    db.refresh(database_user)
    AuditLogService().create_log(
        db=db,
        action="user.deactivate",
        resource_type="user",
        resource_id=database_user.id,
        user_id=database_user.id,
        changes={"is_active": {"old": True, "new": False}},
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
