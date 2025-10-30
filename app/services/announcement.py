from app.models.announcement import Announcement
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
)
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.services.audit_log_service import AuditLogService
from fastapi import Request
from datetime import datetime


class AnnouncementService:
    def __init__(self, db: Session):
        self.db = db

    def create_announcement(
        self,
        announcement_data: AnnouncementCreate,
        request: Request,
        current_user: dict,
    ):
        new_announcement = Announcement(**announcement_data.model_dump())
        self.db.add(new_announcement)
        self.db.commit()
        self.db.refresh(new_announcement)
        AuditLogService().create_log(
            db=self.db,
            action="announcement.create",
            resource_type="announcement",
            resource_id=new_announcement.id,
            user_id=current_user.get("id"),
            status="success",
            status_code=status.HTTP_201_CREATED,
            request_method=request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            request_path=request.url.path,
        )
        return new_announcement

    def get_announcements(self):
        return (
            self.db.query(Announcement)
            .filter(Announcement.expires_at > datetime.now())
            .all()
        )

    def update_announcement(
        self,
        announcement_id: int,
        announcement_data: AnnouncementUpdate,
        request: Request,
        current_user: dict,
    ):
        announcement = (
            self.db.query(Announcement)
            .filter(Announcement.id == announcement_id)
            .first()
        )
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        if announcement_data.title is not None:
            announcement.title = announcement_data.title
        if announcement_data.content is not None:
            announcement.content = announcement_data.content
        if announcement_data.link is not None:
            announcement.link = announcement_data.link
        if announcement_data.expires_at is not None:
            announcement.expires_at = announcement_data.expires_at
        self.db.commit()
        self.db.refresh(announcement)
        AuditLogService().create_log(
            db=self.db,
            action="announcement.update",
            resource_type="announcement",
            resource_id=announcement_id,
            user_id=current_user.get("id"),
            status="success",
            status_code=status.HTTP_200_OK,
            request_method=request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            request_path=request.url.path,
        )
        return announcement

    def delete_announcement(
        self, announcement_id: int, request: Request, current_user: dict
    ):
        announcement = (
            self.db.query(Announcement)
            .filter(Announcement.id == announcement_id)
            .first()
        )
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        self.db.delete(announcement)
        self.db.commit()
        AuditLogService().create_log(
            db=self.db,
            action="announcement.delete",
            resource_type="announcement",
            resource_id=announcement_id,
            user_id=current_user.get("id"),
            status="success",
            status_code=status.HTTP_200_OK,
            request_method=request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            request_path=request.url.path,
        )
        return announcement
