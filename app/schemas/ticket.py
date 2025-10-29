from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.models.ticket import TicketStatus


class TicketBase(BaseModel):
    title: str


class TicketCreate(TicketBase):
    pass  # Only title required when creating


class MessageBase(BaseModel):
    message: str


class MessageCreate(MessageBase):
    pass  # message text only


class MessageResponse(MessageBase):
    id: int
    ticket_id: int
    sender_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        orm_mode = True


class TicketResponse(TicketBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    messages: Optional[List[MessageResponse]] = []
    user: UserResponse

    class Config:
        orm_mode = True


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[TicketStatus] = None
