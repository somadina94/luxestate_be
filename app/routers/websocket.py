from typing import Annotated
from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.auth_service import get_current_user
from app.websocket.chat import chat_websocket

router = APIRouter(prefix="/ws", tags=["ws"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.websocket("/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket, db: db_dependency, conversation_id: int
):
    token = websocket.query_params.get("token")
    user = get_current_user(token)
    await chat_websocket(websocket, conversation_id, db)
