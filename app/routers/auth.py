from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.database import SessionLocal
from ..services.auth_service import (
    create_access_token,
    get_current_user,
    get_password_hash,
    authenticate_user,
)
from ..schemas.user import UserCreate, Token
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.utils.email_utils import send_verification_email
import hashlib
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(db: db_dependency, request: UserCreate, http_req: Request):
    user_model = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role,
        phone=request.phone,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(user_model)
    db.commit()
    db.refresh(user_model)

    AuditLogService().create_log(
        db=db,
        action="user.create",
        resource_type="user",
        resource_id=user_model.id,
        user_id=user_model.id,
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
    http_req: Request,
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        AuditLogService().create_log(
            db=db,
            action="auth.login",
            resource_type="auth",
            user_id=None,
            status="failure",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_message="invalid_credentials",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not autheticate user",
        )
    if user.is_active == False:
        AuditLogService().create_log(
            db=db,
            action="auth.login",
            resource_type="auth",
            user_id=user.id,
            status="failure",
            status_code=HTTP_400_BAD_REQUEST,
            error_message="account_inactive",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="You deativated your account, contact suuport to reactivate or completely delete your information",
        )
    code = str(random.randint(100000, 999999))
    await send_verification_email(user.email, code)
    hashed_code = hashlib.sha256(code.encode()).hexdigest()
    database_user = db.query(User).filter(User.id == user.id).first()
    database_user.verification_code = hashed_code
    database_user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    db.refresh(database_user)
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=60)
    )
    result = {
        "access_token": token,
        "token_type": "bearer",
        "message": "Login access token sent to your email",
    }
    AuditLogService().create_log(
        db=db,
        action="auth.login",
        resource_type="auth",
        user_id=user.id,
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return result


@router.post("/verify-login/{access_token}", response_model=Token)
async def verify_login(db: db_dependency, access_token: str, http_req: Request):
    input_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    user = db.query(User).filter(User.verification_code == input_token_hash).first()
    if not user:
        AuditLogService().create_log(
            db=db,
            action="auth.verify",
            resource_type="auth",
            user_id=None,
            status="failure",
            status_code=HTTP_404_NOT_FOUND,
            error_message="verification_not_found",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=60)
    )
    user.verification_code = None
    user.verification_code_expires = None
    user.is_verified = True
    db.commit()
    db.refresh(user)
    AuditLogService().create_log(
        db=db,
        action="auth.verify",
        resource_type="auth",
        user_id=user.id,
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot_password", status_code=status.HTTP_200_OK)
async def forgot_password(db: db_dependency, email: str, http_req: Request):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        AuditLogService().create_log(
            db=db,
            action="auth.password_reset_request",
            resource_type="auth",
            user_id=None,
            status="failure",
            status_code=HTTP_404_NOT_FOUND,
            error_message="user_not_found",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="User does not exist"
        )
    code = str(random.randint(100000, 999999))
    await send_verification_email(user.email, code)
    hashed_code = hashlib.sha256(code.encode()).hexdigest()
    user.verification_code = hashed_code
    user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    db.refresh(user)
    AuditLogService().create_log(
        db=db,
        action="auth.password_reset_request",
        resource_type="auth",
        user_id=user.id,
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {
        "message": "Reset token sent to your email",
    }


@router.patch("/reset_password", status_code=status.HTTP_200_OK)
async def reset_password(
    db: db_dependency,
    new_password: str,
    confirm_password: str,
    access_token: str,
    http_req: Request,
):
    input_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    user = db.query(User).filter(User.verification_code == input_token_hash).first()
    if not user:
        AuditLogService().create_log(
            db=db,
            action="auth.password_reset",
            resource_type="auth",
            user_id=None,
            status="failure",
            status_code=HTTP_404_NOT_FOUND,
            error_message="verification_not_found",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    if new_password != confirm_password:
        AuditLogService().create_log(
            db=db,
            action="auth.password_reset",
            resource_type="auth",
            user_id=user.id,
            status="failure",
            status_code=HTTP_400_BAD_REQUEST,
            error_message="password_mismatch",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Password and Confirm Password do not match",
        )
    user.password_hash = crypt_context.hash(new_password)
    user.verification_code = None
    user.verification_code_expires = None
    db.commit()
    db.refresh(user)
    AuditLogService().create_log(
        db=db,
        action="auth.password_reset",
        resource_type="auth",
        user_id=user.id,
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"message": "Password reset successful, please go ahead and login"}


@router.patch("/update_password", status_code=HTTP_200_OK)
def update_password(
    db: db_dependency,
    user: user_dependency,
    current_password: str,
    new_password: str,
    confirm_password: str,
    http_req: Request,
):
    database_user = db.query(User).filter(User.id == user.get("id")).first()
    if not database_user:
        AuditLogService().create_log(
            db=db,
            action="auth.password_update",
            resource_type="auth",
            user_id=user.get("id"),
            status="failure",
            status_code=HTTP_404_NOT_FOUND,
            error_message="user_not_found",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    if not crypt_context.verify(current_password, database_user.password_hash):
        AuditLogService().create_log(
            db=db,
            action="auth.password_update",
            resource_type="auth",
            user_id=database_user.id,
            status="failure",
            status_code=HTTP_400_BAD_REQUEST,
            error_message="wrong_current_password",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Wrong current password"
        )
    if new_password != confirm_password:
        AuditLogService().create_log(
            db=db,
            action="auth.password_update",
            resource_type="auth",
            user_id=database_user.id,
            status="failure",
            status_code=HTTP_400_BAD_REQUEST,
            error_message="password_mismatch",
            ip_address=http_req.headers.get("x-forwarded-for")
            or (http_req.client.host if http_req.client else None),
            user_agent=http_req.headers.get("user-agent"),
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Password and Confirm Password do not match",
        )
    database_user.password_hash = crypt_context.hash(new_password)
    database_user.verification_code = None
    database_user.verification_code_expires = None
    db.commit()
    db.refresh(database_user)
    AuditLogService().create_log(
        db=db,
        action="auth.password_update",
        resource_type="auth",
        user_id=database_user.id,
        status="success",
        status_code=HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for")
        or (http_req.client.host if http_req.client else None),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"message": "Password updated successfully"}
