from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED
from app.database import SessionLocal
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session
from app.services.auth_service import get_current_user
from app.dependencies import db_dependency, require_permission, Permission

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(require_permission(Permission.MANAGE_USERS))]


@router.get("/users", status_code=status.HTTP_200_OK)
def get_all_users(user: user_dependency, db: db_dependency):
    return db.query(User).all()
