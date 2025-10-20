from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.database import SessionLocal
from ..services.auth_service import (
    create_access_token,
    get_password_hash,
    authenticate_user,
)
from ..schemas.user import UserCreate, Token
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


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


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not autheticate user",
        )
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=60)
    )
    return {"access_token": token, "token_type": "bearer"}
