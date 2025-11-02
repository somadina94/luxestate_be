from typing import Annotated
from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.websocket.chat import chat_websocket_multi

router = APIRouter(prefix="/ws", tags=["ws"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


@router.websocket("/multi")
async def websocket_multi_endpoint(websocket: WebSocket, db: db_dependency):
    """Multi-conversation WebSocket endpoint - one connection handles multiple conversations.

    Connect to: ws://host/ws/multi?token=your_token

    Message types:
    - subscribe: {"type": "subscribe", "conversation_id": 123}
    - unsubscribe: {"type": "unsubscribe", "conversation_id": 123}
    - message: {"type": "message", "conversation_id": 123, "content": "Hello"}
    - read: {"type": "read", "conversation_id": 123, "message_ids": [1, 2, 3]}
    """
    await chat_websocket_multi(websocket, db)
