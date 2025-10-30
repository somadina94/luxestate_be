from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AnnouncementBase(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=1000)
    link: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = Field(None)


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(AnnouncementBase):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, max_length=1000)
    link: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = Field(None)


class AnnouncementResponse(AnnouncementBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = Field(None)
    
    class Config:
        from_attributes = True