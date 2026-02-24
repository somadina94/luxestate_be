from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import SessionLocal
from app.services.auth_service import get_current_user
from app.models.chat import Conversation, Message
from app.models.user import User
from app.models.property import Property
from app.schemas.chat import ConversationCreate, ConversationResponse, MessageResponse
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


@router.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(
    db: db_dependency,
    user: user_dependency,
    http_req: Request,
):
    """Get all conversations where the current user is a participant.

    Returns conversations where the user is:
    - user_id (the owner)
    - agent_id (assigned agent)
    - admin_id (assigned admin)

    This is the endpoint the frontend uses to get conversation_ids
    for subscribing to WebSocket connections.
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conversations = (
        db.query(Conversation)
        .filter(
            or_(
                Conversation.user_id == user_id,
                Conversation.agent_id == user_id,
                Conversation.admin_id == user_id,
            )
        )
        .all()
    )

    AuditLogService().create_log(
        db=db,
        action="chat.conversations_listed",
        resource_type="conversation",
        resource_id=None,
        user_id=user_id,
        status="success",
        status_code=200,
        request_method=http_req.method,
        request_path=http_req.url.path,
    )

    return conversations


@router.post("/create", response_model=ConversationResponse)
def create_conversation(
    request: ConversationCreate,
    db: db_dependency,
    user: user_dependency,
    http_req: Request,
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
    convo = Conversation(**request.model_dump())
    # Populate display snapshot from User and Property
    user_entity = db.query(User).filter(User.id == request.user_id).first()
    if user_entity:
        convo.user_first_name = user_entity.first_name
        convo.user_last_name = user_entity.last_name
    if request.agent_id:
        agent_entity = db.query(User).filter(User.id == request.agent_id).first()
        if agent_entity:
            convo.agent_first_name = agent_entity.first_name
            convo.agent_last_name = agent_entity.last_name
    if request.property_id:
        prop = db.query(Property).filter(Property.id == request.property_id).first()
        if prop:
            convo.property_title = prop.title
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


@router.get("/messages/{conversation_id}", response_model=List[MessageResponse])
def get_messages(
    conversation_id: int,
    db: db_dependency,
    user: user_dependency,
    http_req: Request,
):
    messages = (
        db.query(Message).filter(Message.conversation_id == conversation_id).all()
    )
    AuditLogService().create_log(
        db=db,
        action="chat.messages_listed",
        resource_type="message",
        resource_id=conversation_id,
        user_id=user.get("id"),
        status="success",
        status_code=200,
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return messages


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: int,
    db: db_dependency,
    user: user_dependency,
    http_req: Request,
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .filter(
            or_(
                Conversation.user_id == user.get("id"),
                Conversation.agent_id == user.get("id"),
                Conversation.admin_id == user.get("id"),
            )
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()
    AuditLogService().create_log(
        db=db,
        action="chat.conversation_deleted",
        resource_type="conversation",
        resource_id=conversation_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"detail": "Conversation deleted successfully"}
