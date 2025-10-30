from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, WebSocket, Request
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.auth_service import get_current_user
from app.models.chat import Conversation
from app.schemas.chat import ConversationCreate, ConversationResponse
from app.services.audit_log_service import AuditLogService

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
    request: ConversationCreate, db: db_dependency, user: user_dependency, http_req: Request
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
        AuditLogService().create_log(
            db=db,
            action="chat.conversation_get_or_create",
            resource_type="conversation",
            resource_id=existing_convo.id,
            user_id=user.get("id"),
            status="success",
            status_code=200,
            request_method=http_req.method,
            request_path=http_req.url.path,
        )
        return existing_convo
    convo = Conversation(**request.dict())
    db.add(convo)
    db.commit()
    db.refresh(convo)
    AuditLogService().create_log(
        db=db,
        action="chat.conversation_created",
        resource_type="conversation",
        resource_id=convo.id,
        user_id=user.get("id"),
        status="success",
        status_code=200,
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return convo
