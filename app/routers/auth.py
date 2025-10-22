from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, status, HTTPException
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
def create_user(db: db_dependency, request: UserCreate):
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


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not autheticate user",
        )
    if user.is_active == False:
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
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": "Login access token sent to your email",
    }


@router.post("/verify-login/{access_token}", response_model=Token)
async def verify_login(db: db_dependency, access_token: str):
    input_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    user = db.query(User).filter(User.verification_code == input_token_hash).first()
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=60)
    )
    user.verification_code = None
    user.verification_code_expires = None
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot_password", status_code=status.HTTP_200_OK)
async def forgot_password(db: db_dependency, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
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
    return {
        "message": "Reset token sent to your email",
    }


@router.patch("/reset_password", status_code=status.HTTP_200_OK)
async def reset_password(
    db: db_dependency, new_password: str, confirm_password: str, access_token: str
):
    input_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    user = db.query(User).filter(User.verification_code == input_token_hash).first()
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    if new_password != confirm_password:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Password and Confirm Password do not match",
        )
    user.password_hash = crypt_context.hash(new_password)
    user.verification_code = None
    user.verification_code_expires = None
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successful, please go ahead and login"}


@router.patch("/update_password", status_code=HTTP_200_OK)
def update_password(
    db: db_dependency,
    user: user_dependency,
    current_password: str,
    new_password: str,
    confirm_password: str,
):
    database_user = db.query(User).filter(User.id == user.get("id")).first()
    if not database_user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    if not crypt_context.verify(current_password, database_user.password_hash):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Wrong current password"
        )
    if new_password != confirm_password:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Password and Confirm Password do not match",
        )
    database_user.password_hash = crypt_context.hash(new_password)
    database_user.verification_code = None
    database_user.verification_code_expires = None
    db.commit()
    db.refresh(database_user)
    return {"message": "Password updated successfully"}
