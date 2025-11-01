import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.chat import Message, Conversation
from app.services.auth_service import decode_token
from app.services.notifications import dispatch_notification
from app.services.audit_log_service import AuditLogService
from datetime import datetime, timezone


# in-memory managers
class ConnectionManager:
    def __init__(self):
        # conversation_id -> list[WebSocket]
        self.by_conversation: Dict[int, List[WebSocket]] = {}
        # user_id -> list[WebSocket]
        self.by_user: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, conversation_id: int, websocket: WebSocket):
        await websocket.accept()
        self.by_conversation.setdefault(conversation_id, []).append(websocket)
        self.by_user.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, conversation_id: int, websocket: WebSocket):
        if (
            conversation_id in self.by_conversation
            and websocket in self.by_conversation[conversation_id]
        ):
            self.by_conversation[conversation_id].remove(websocket)
            if not self.by_conversation[conversation_id]:
                del self.by_conversation[conversation_id]
        if user_id in self.by_user and websocket in self.by_user[user_id]:
            self.by_user[user_id].remove(websocket)
            if not self.by_user[user_id]:
                del self.by_user[user_id]

    async def send_to_conversation(self, conversation_id: int, event: dict):
        if conversation_id not in self.by_conversation:
            return
        payload = json.dumps(event)
        disconnected = []
        for ws in list(self.by_conversation[conversation_id]):
            try:
                await ws.send_text(payload)
            except:
                disconnected.append(ws)
        # cleanup
        for ws in disconnected:
            for uid, sockets in list(self.by_user.items()):
                if ws in sockets:
                    sockets.remove(ws)
                    if not sockets:
                        del self.by_user[uid]
            if (
                conversation_id in self.by_conversation
                and ws in self.by_conversation[conversation_id]
            ):
                self.by_conversation[conversation_id].remove(ws)

    async def is_user_online(self, user_id: int) -> bool:
        return user_id in self.by_user and len(self.by_user[user_id]) > 0

    async def send_to_user(self, user_id: int, event: dict):
        # send to all sockets for this user
        if user_id not in self.by_user:
            return
        payload = json.dumps(event)
        disconnected = []
        for ws in list(self.by_user[user_id]):
            try:
                await ws.send_text(payload)
            except:
                disconnected.append(ws)
        for ws in disconnected:
            self.by_user[user_id].remove(ws)
            # optionally cleanup by_conversation as well
            for conv_id, sockets in list(self.by_conversation.items()):
                if ws in sockets:
                    sockets.remove(ws)
                    if not sockets:
                        del self.by_conversation[conv_id]


manager = ConnectionManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def chat_websocket(websocket: WebSocket, conversation_id: int, db: Session):
    # --- authenticate via token query param ---
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        # Log unauthorized connect attempt
        AuditLogService().create_log(
            db=db,
            action="chat.ws_connect",
            resource_type="chat",
            resource_id=conversation_id,
            user_id=None,
            status="failure",
            status_code=4401,
            error_message="missing_token",
        )
        return

    try:
        user = await decode_token(token)  # returns dict with id,email,role
    except Exception:
        await websocket.close(code=4401)
        AuditLogService().create_log(
            db=db,
            action="chat.ws_connect",
            resource_type="chat",
            resource_id=conversation_id,
            user_id=None,
            status="failure",
            status_code=4401,
            error_message="invalid_token",
        )
        return

    # --- verify conversation ---
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        await websocket.close(code=4404)
        AuditLogService().create_log(
            db=db,
            action="chat.ws_connect",
            resource_type="chat",
            resource_id=conversation_id,
            user_id=user.get("id") if isinstance(user, dict) else None,
            status="failure",
            status_code=4404,
            error_message="conversation_not_found",
        )
        return

    if user["id"] not in [
        conversation.user_id,
        conversation.agent_id,
        conversation.admin_id,
    ]:
        await websocket.close(code=4403)
        AuditLogService().create_log(
            db=db,
            action="chat.ws_connect",
            resource_type="chat",
            resource_id=conversation_id,
            user_id=user["id"],
            status="failure",
            status_code=4403,
            error_message="forbidden",
        )
        return

    # connect
    await manager.connect(
        user_id=user["id"], conversation_id=conversation_id, websocket=websocket
    )
    AuditLogService().create_log(
        db=db,
        action="chat.ws_connect",
        resource_type="chat",
        resource_id=conversation_id,
        user_id=user["id"],
        status="success",
        status_code=101,
    )

    try:
        while True:
            try:
                # expecting JSON: { "content": "...", "type": "message" }
                data = await websocket.receive_json()
            except Exception:
                # invalid json or client closed; gracefully continue/close
                continue

            msg_type = data.get("type", "message")
            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue

                # persist message (use authenticated user id)
                message = Message(
                    conversation_id=conversation_id,
                    sender_id=user["id"],
                    content=content,
                    # optionally add timestamp/is_read
                )
                db.add(message)
                db.commit()
                db.refresh(message)

                # Log message metadata (no content)
                AuditLogService().create_log(
                    db=db,
                    action="chat.message_sent",
                    resource_type="chat",
                    resource_id=conversation_id,
                    user_id=user["id"],
                    status="success",
                    status_code=200,
                )

                # build event
                event = {
                    "type": "new_message",
                    "conversation_id": conversation_id,
                    "message": {
                        "id": message.id,
                        "conversation_id": conversation_id,
                        "sender_id": user["id"],
                        "content": content,
                        "timestamp": (
                            message.timestamp.isoformat()
                            if hasattr(message, "timestamp")
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    },
                }

                # send real-time to conversation participants
                await manager.send_to_conversation(conversation_id, event)

                # determine recipient id(s) — 1-to-1
                recipient_id = None
                if user["id"] == conversation.user_id:
                    recipient_id = conversation.agent_id or conversation.admin_id
                else:
                    recipient_id = conversation.user_id

                # if recipient online -> send delivered / push may not be necessary
                recipient_online = await manager.is_user_online(recipient_id)
                if recipient_online:
                    # mark delivered maybe in DB (optional)
                    delivered_event = {
                        "type": "delivered",
                        "conversation_id": conversation_id,
                        "message_id": message.id,
                        "to": recipient_id,
                    }
                    # send to recipient sockets
                    await manager.send_to_user(recipient_id, delivered_event)
                else:
                    # recipient offline -> dispatch push & email in background
                    title = "New message"
                    body = content if len(content) < 200 else content[:197] + "..."
                    payload = {
                        "conversation_id": conversation_id,
                        "message_id": message.id,
                    }
                    # run blocking dispatch in background thread
                    asyncio.create_task(
                        asyncio.to_thread(
                            dispatch_notification, recipient_id, title, body, payload
                        )
                    )

            elif msg_type == "read":
                # client informs that messages are read
                message_ids = data.get("message_ids", [])
                # mark read in DB
                if message_ids:
                    db.query(Message).filter(Message.id.in_(message_ids)).update(
                        {"is_read": True}, synchronize_session=False
                    )
                    db.commit()
                    AuditLogService().create_log(
                        db=db,
                        action="chat.read_receipt",
                        resource_type="chat",
                        resource_id=conversation_id,
                        user_id=user["id"],
                        status="success",
                        status_code=200,
                    )
                    # notify sender(s) that messages were read
                    read_event = {
                        "type": "read_receipt",
                        "message_ids": message_ids,
                        "conversation_id": conversation_id,
                        "by": user["id"],
                    }
                    # send to conversation
                    await manager.send_to_conversation(conversation_id, read_event)

            # other types can be added: typing, seen, etc.

    except WebSocketDisconnect:
        manager.disconnect(
            user_id=user["id"], conversation_id=conversation_id, websocket=websocket
        )
        AuditLogService().create_log(
            db=db,
            action="chat.ws_disconnect",
            resource_type="chat",
            resource_id=conversation_id,
            user_id=user["id"],
            status="success",
            status_code=1000,
        )
