from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.announcement import AnnouncementService
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
)
from app.dependencies import require_permission, Permission

router = APIRouter(prefix="/announcements", tags=["announcements"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
admin_dependency = Annotated[
    dict, Depends(require_permission(Permission.MANAGE_ANNOUNCEMENTS))
]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AnnouncementResponse)
def create_announcement(
    announcement_data: AnnouncementCreate,
    db: db_dependency,
    request: Request,
    current_user: admin_dependency,
):
    return AnnouncementService(db).create_announcement(
        announcement_data, request, current_user
    )


@router.get("/", status_code=status.HTTP_200_OK, response_model=list[AnnouncementResponse])
def get_announcements(db: db_dependency):
    return AnnouncementService(db).get_announcements()


@router.put("/{announcement_id}", status_code=status.HTTP_200_OK, response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    announcement_data: AnnouncementUpdate,
    db: db_dependency,
    request: Request,
    current_user: admin_dependency,
):
    return AnnouncementService(db).update_announcement(
        announcement_id, announcement_data, request, current_user
    )


@router.delete("/{announcement_id}", status_code=status.HTTP_200_OK, response_model=AnnouncementResponse)
def delete_announcement(
    announcement_id: int,
    db: db_dependency,
    request: Request,
    current_user: admin_dependency,
):
    return AnnouncementService(db).delete_announcement(
        announcement_id, request, current_user
    )
