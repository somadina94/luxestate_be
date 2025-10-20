from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated, List, Optional

from sqlalchemy.orm import Session
from starlette import status
from app.database import SessionLocal
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse

from app.dependencies import get_current_user, require_permission, Permission
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["properties"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[
    dict, Depends(require_permission(Permission.CREATE_PROPERTIES))
]


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    db: db_dependency,
    property: PropertyCreate,
    current_user: user_dependency,
):
    return await PropertyService().create_property(
        db=db, property_data=property, agent_id=current_user.get("id")
    )


@router.get("/", status_code=status.HTTP_200_OK)
async def get_properties(db: db_dependency):
    return await PropertyService().get_properties(db)


@router.get("/{property_id}", status_code=status.HTTP_200_OK)
async def get_property(db: db_dependency, property_id: int):
    return await PropertyService().get_property(db, property_id)


@router.patch("/{property_id}", status_code=status.HTTP_200_OK)
async def update_property(
    db: db_dependency, property: PropertyUpdate, user: user_dependency, property_id: int
):
    return await PropertyService().update_property(
        db, property_id, property, user.get("id")
    )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(db: db_dependency, user: user_dependency, property_id: int):
    return await PropertyService().delete_property(db, property_id, user.get("id"))
