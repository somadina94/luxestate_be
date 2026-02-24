from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    user_id: int
    agent_id: int | None = None
    property_id: int | None = None
    type: str


class ConversationResponse(ConversationCreate):
    id: int
    user_first_name: str | None = None
    user_last_name: str | None = None
    agent_first_name: str | None = None
    agent_last_name: str | None = None
    property_title: str | None = None

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
    created_at: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)
