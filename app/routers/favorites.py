from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated, List
from app.database import SessionLocal
from app.models.favorite import Favorite
from app.models.property import Property
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post(
    "/{property_id}",
    response_model=FavoriteResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite(
    property_id: int,
    db: db_dependency,
    current_user: user_dependency,
):
    # Validate property exists
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Idempotent: return existing
    existing = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user["id"], Favorite.property_id == property_id
        )
        .first()
    )
    if existing:
        return existing

    fav = Favorite(user_id=current_user["id"], property_id=property_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    property_id: int,
    db: db_dependency,
    current_user: user_dependency,
):
    fav = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user["id"], Favorite.property_id == property_id
        )
        .first()
    )
    if not fav:
        return
    db.delete(fav)
    db.commit()


@router.get("/me", response_model=List[FavoriteResponse])
def list_my_favorites(db: db_dependency, current_user: user_dependency):
    return db.query(Favorite).filter(Favorite.user_id == current_user["id"]).all()
