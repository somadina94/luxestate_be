from pydantic import BaseModel, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(TicketBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    messages: Optional[List[MessageResponse]] = []
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[TicketStatus] = None
