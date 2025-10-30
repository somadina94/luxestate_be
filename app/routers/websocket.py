from typing import Annotated
from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.websocket.chat import chat_websocket

router = APIRouter(prefix="/ws", tags=["ws"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


@router.websocket("/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket, db: db_dependency, conversation_id: int
):
    await chat_websocket(websocket, conversation_id, db)
