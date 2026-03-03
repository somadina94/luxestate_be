from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    user_id: int
    agent_id: Optional[int] = None
    property_id: Optional[int] = None
    type: str


class ConversationResponse(ConversationCreate):
    id: int
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    agent_first_name: Optional[str] = None
    agent_last_name: Optional[str] = None
    property_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    conversation_id: int
    sender_id: int
    content: str

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(MessageCreate):
    id: int
    conversation_id: int
    sender_id: int
    created_at: datetime = Field(validation_alias="timestamp")
    is_read: bool

    model_config = ConfigDict(from_attributes=True)
