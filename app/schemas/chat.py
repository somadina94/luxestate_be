from pydantic import BaseModel


class ConversationCreate(BaseModel):
    user_id: int
    agent_id: int | None = None
    admin_id: int | None = None
    property_id: int | None = None
    type: str


class ConversationResponse(ConversationCreate):
    id: int

    class Config:
        orm_mode = True
