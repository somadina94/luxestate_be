from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.auth_service import get_current_user
from app.models.chat import Conversation
from app.schemas.chat import ConversationCreate, ConversationResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/create", response_model=ConversationResponse)
def create_conversation(
    request: ConversationCreate, db: db_dependency, user: user_dependency
):
    existing_convo = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == request.user_id,
            Conversation.agent_id == request.agent_id,
            Conversation.property_id == request.property_id,
            Conversation.type == request.type,
        )
        .first()
    )
    if existing_convo:
        return existing_convo
    convo = Conversation(**request.dict())
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo
