from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    user_id: int
    agent_id: int | None = None
    property_id: int | None = None
    type: str


class ConversationResponse(ConversationCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
