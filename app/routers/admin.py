from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.database import SessionLocal
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/users", status_code=status.HTTP_200_OK)
def get_all_users(user: user_dependency, db: db_dependency):
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not autheticate user",
        )
    return db.query(User).all()
