from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED
from app.database import SessionLocal
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/", status_code=status.HTTP_200_OK)
def get_me(user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return db.query(User).filter(User.id == user.get("id")).first()


@router.delete("/deactivate", status_code=status.HTTP_200_OK)
def deactivate_user(db: db_dependency, user: user_dependency):
    database_user: User = db.query(User).filter(User.id == user.get("id")).first()
    database_user.is_active = False
    db.commit()
    db.refresh(database_user)
