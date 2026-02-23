from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Annotated, List
from app.database import SessionLocal
from app.models.favorite import Favorite
from app.models.property import Property
from app.schemas.favorite import FavoriteResponse
from app.services.auth_service import get_current_user
from app.services.audit_log_service import AuditLogService

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
    request: Request,
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

    fav = Favorite(
        user_id=current_user["id"],
        property_id=property_id,
        overview_image=prop.overview_image,
        address=prop.address,
        price=prop.price,
        currency=prop.currency,
        year_built=prop.year_built,
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)

    AuditLogService().create_log(
        db=db,
        action="favorite.create",
        resource_type="favorite",
        resource_id=fav.id,
        user_id=current_user["id"],
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )

    return fav


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    property_id: int,
    db: db_dependency,
    current_user: user_dependency,
    request: Request,
):
    fav = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user["id"], Favorite.property_id == property_id
        )
        .first()
    )
    if not fav:
        # Log idempotent delete attempt as success with no resource
        AuditLogService().create_log(
            db=db,
            action="favorite.delete",
            resource_type="favorite",
            resource_id=None,
            user_id=current_user["id"],
            status="success",
            status_code=status.HTTP_204_NO_CONTENT,
            ip_address=request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            request_method=request.method,
            request_path=request.url.path,
        )
        return
    db.delete(fav)
    db.commit()

    AuditLogService().create_log(
        db=db,
        action="favorite.delete",
        resource_type="favorite",
        resource_id=fav.id,
        user_id=current_user["id"],
        status="success",
        status_code=status.HTTP_204_NO_CONTENT,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )


@router.get("/me", response_model=List[FavoriteResponse])
def list_my_favorites(
    db: db_dependency, current_user: user_dependency, request: Request
):
    rows = db.query(Favorite).filter(Favorite.user_id == current_user["id"]).all()
    # Low-priority read log
    AuditLogService().create_log(
        db=db,
        action="favorite.list",
        resource_type="favorite",
        resource_id=None,
        user_id=current_user["id"],
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return rows
