from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from app.database import SessionLocal
from app.models.user import User
from typing import Annotated
from sqlalchemy.orm import Session
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


@router.patch("/suspend/{user_id}", status_code=status.HTTP_200_OK)
async def suspend_user(db: db_dependency, user: user_dependency, user_id: int):
    user_to_suspend: User = db.query(User).filter(User.id == user_id).first()
    if not user_to_suspend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_to_suspend.is_active = False
    db.commit()
    db.refresh(user_to_suspend)
    return {"message": "User suspended successfully"}


@router.patch("/unsuspend/{user_id}", status_code=status.HTTP_200_OK)
async def unsuspend_user(db: db_dependency, user: user_dependency, user_id: int):
    user_to_unsuspend: User = db.query(User).filter(User.id == user_id).first()
    if not user_to_unsuspend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_to_unsuspend.is_active = True
    db.commit()
    db.refresh(user_to_unsuspend)
    return {"message": "User unsuspended successfully"}
