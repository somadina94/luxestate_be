import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
        # websocket -> set of conversation_ids (for multi-conversation support)
        self.subscriptions: Dict[WebSocket, set] = {}
        # websocket -> user_id mapping
        self.websocket_to_user: Dict[WebSocket, int] = {}

    async def connect_multi(self, user_id: int, websocket: WebSocket):
        """Connect a WebSocket for multi-conversation support."""
        await websocket.accept()
        self.by_user.setdefault(user_id, []).append(websocket)
        self.subscriptions[websocket] = set()
        self.websocket_to_user[websocket] = user_id

    async def subscribe(self, websocket: WebSocket, conversation_id: int, user_id: int):
        """Subscribe a WebSocket to a conversation."""
        if websocket not in self.subscriptions:
            self.subscriptions[websocket] = set()
        self.subscriptions[websocket].add(conversation_id)
        # Also add to by_conversation for broadcasting
        if websocket not in self.by_conversation.get(conversation_id, []):
            self.by_conversation.setdefault(conversation_id, []).append(websocket)

    async def unsubscribe(self, websocket: WebSocket, conversation_id: int):
        """Unsubscribe a WebSocket from a conversation."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(conversation_id)
        # Remove from by_conversation
        if conversation_id in self.by_conversation:
            if websocket in self.by_conversation[conversation_id]:
                self.by_conversation[conversation_id].remove(websocket)
            if not self.by_conversation[conversation_id]:
                del self.by_conversation[conversation_id]

    def disconnect_multi(self, websocket: WebSocket):
        """Disconnect a multi-conversation WebSocket and cleanup all subscriptions."""
        user_id = self.websocket_to_user.get(websocket)
        if user_id:
            # Remove from by_user
            if user_id in self.by_user and websocket in self.by_user[user_id]:
                self.by_user[user_id].remove(websocket)
                if not self.by_user[user_id]:
                    del self.by_user[user_id]
            # Remove all conversation subscriptions
            if websocket in self.subscriptions:
                for conversation_id in list(self.subscriptions[websocket]):
                    if conversation_id in self.by_conversation:
                        if websocket in self.by_conversation[conversation_id]:
                            self.by_conversation[conversation_id].remove(websocket)
                        if not self.by_conversation[conversation_id]:
                            del self.by_conversation[conversation_id]
                del self.subscriptions[websocket]
            del self.websocket_to_user[websocket]

    async def send_to_conversation(self, conversation_id: int, event: dict):
        if conversation_id not in self.by_conversation:
            return
        payload = json.dumps(event)
        disconnected = []
        for ws in list(self.by_conversation[conversation_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect_multi(ws)

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
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect_multi(ws)


manager = ConnectionManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def chat_websocket_multi(websocket: WebSocket, db: Session):
    """Multi-conversation WebSocket handler - one connection handles multiple conversations."""
    # --- authenticate via token query param ---
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        AuditLogService().create_log(
            db=db,
            action="chat.ws_connect_multi",
            resource_type="chat",
            resource_id=None,
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
            action="chat.ws_connect_multi",
            resource_type="chat",
            resource_id=None,
            user_id=None,
            status="failure",
            status_code=4401,
            error_message="invalid_token",
        )
        return

    # connect without conversation_id — wrap all post-auth logic so no exception propagates
    # (framework would send HTTP error on WS scope -> RuntimeError)
    try:
        await manager.connect_multi(user_id=user["id"], websocket=websocket)

        # Auto-subscribe to all conversations user is part of
        conversations = (
            db.query(Conversation)
            .filter(
                or_(
                    Conversation.user_id == user["id"],
                    Conversation.agent_id == user["id"],
                    Conversation.admin_id == user["id"],
                )
            )
            .all()
        )

        subscribed_count = 0
        for conversation in conversations:
            await manager.subscribe(websocket, conversation.id, user["id"])
            subscribed_count += 1

        # Send confirmation with subscribed conversations
        await websocket.send_json(
            {
                "type": "connected",
                "message": "WebSocket connected and auto-subscribed to conversations",
                "subscribed_conversations": [conv.id for conv in conversations],
                "count": subscribed_count,
            }
        )

        AuditLogService().create_log(
            db=db,
            action="chat.ws_connect_multi",
            resource_type="chat",
            resource_id=None,
            user_id=user["id"],
            status="success",
            status_code=101,
        )

        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break  # Exit loop; cleanup in finally (do not re-raise or framework sends HTTP response on WS scope)
            except Exception:
                continue

            msg_type = data.get("type", "message")

            if msg_type == "subscribe":
                # Subscribe to a conversation
                conversation_id = data.get("conversation_id")
                if not conversation_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "conversation_id is required for subscribe",
                        }
                    )
                    continue

                try:
                    conversation_id = int(conversation_id)
                except (ValueError, TypeError):
                    await websocket.send_json(
                        {"type": "error", "message": "invalid conversation_id"}
                    )
                    continue

                # Verify conversation exists and user has access
                conversation = (
                    db.query(Conversation)
                    .filter(Conversation.id == conversation_id)
                    .first()
                )
                if not conversation:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "conversation_not_found",
                            "conversation_id": conversation_id,
                        }
                    )
                    continue

                if user["id"] not in [
                    conversation.user_id,
                    conversation.agent_id,
                    conversation.admin_id,
                ]:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "forbidden",
                            "conversation_id": conversation_id,
                        }
                    )
                    continue

                # Subscribe to conversation
                await manager.subscribe(websocket, conversation_id, user["id"])
                await websocket.send_json(
                    {"type": "subscribed", "conversation_id": conversation_id}
                )

                AuditLogService().create_log(
                    db=db,
                    action="chat.ws_subscribe",
                    resource_type="chat",
                    resource_id=conversation_id,
                    user_id=user["id"],
                    status="success",
                    status_code=200,
                )

            elif msg_type == "unsubscribe":
                # Unsubscribe from a conversation
                conversation_id = data.get("conversation_id")
                if not conversation_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "conversation_id is required for unsubscribe",
                        }
                    )
                    continue

                try:
                    conversation_id = int(conversation_id)
                except (ValueError, TypeError):
                    await websocket.send_json(
                        {"type": "error", "message": "invalid conversation_id"}
                    )
                    continue

                await manager.unsubscribe(websocket, conversation_id)
                await websocket.send_json(
                    {"type": "unsubscribed", "conversation_id": conversation_id}
                )

                AuditLogService().create_log(
                    db=db,
                    action="chat.ws_unsubscribe",
                    resource_type="chat",
                    resource_id=conversation_id,
                    user_id=user["id"],
                    status="success",
                    status_code=200,
                )

            elif msg_type == "message":
                # Send a message to a conversation
                conversation_id = data.get("conversation_id")
                content = data.get("content", "").strip()

                if not conversation_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "conversation_id is required for message",
                        }
                    )
                    continue

                if not content:
                    continue

                try:
                    conversation_id = int(conversation_id)
                except (ValueError, TypeError):
                    await websocket.send_json(
                        {"type": "error", "message": "invalid conversation_id"}
                    )
                    continue

                # Verify user is subscribed to this conversation
                if (
                    websocket not in manager.subscriptions
                    or conversation_id not in manager.subscriptions[websocket]
                ):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "not_subscribed_to_conversation",
                            "conversation_id": conversation_id,
                        }
                    )
                    continue

                # Verify conversation exists and user has access
                conversation = (
                    db.query(Conversation)
                    .filter(Conversation.id == conversation_id)
                    .first()
                )
                if not conversation:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "conversation_not_found",
                            "conversation_id": conversation_id,
                        }
                    )
                    continue

                if user["id"] not in [
                    conversation.user_id,
                    conversation.agent_id,
                    conversation.admin_id,
                ]:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "forbidden",
                            "conversation_id": conversation_id,
                        }
                    )
                    continue

                # Persist message
                message = Message(
                    conversation_id=conversation_id,
                    sender_id=user["id"],
                    content=content,
                )
                db.add(message)
                db.commit()
                db.refresh(message)

                AuditLogService().create_log(
                    db=db,
                    action="chat.message_sent",
                    resource_type="chat",
                    resource_id=conversation_id,
                    user_id=user["id"],
                    status="success",
                    status_code=200,
                )

                # Build event
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

                # Send to all participants in the conversation
                await manager.send_to_conversation(conversation_id, event)

                # Determine recipient
                recipient_id = None
                if user["id"] == conversation.user_id:
                    recipient_id = conversation.agent_id or conversation.admin_id
                else:
                    recipient_id = conversation.user_id

                # Handle delivery notifications
                # Note: With multiple workers, connections may be on different workers
                # This check only works for connections on the same worker process
                recipient_online = await manager.is_user_online(recipient_id)

                # Debug logging (helps diagnose multi-worker issues)
                import logging

                logger = logging.getLogger(__name__)
                active_connections = len(
                    manager.by_conversation.get(conversation_id, [])
                )
                logger.info(
                    f"Message sent to conversation {conversation_id}. "
                    f"Recipient {recipient_id} online check: {recipient_online}. "
                    f"Active connections in this worker: {active_connections}. "
                    f"Note: With multiple workers, connections may be on different workers"
                )

                if recipient_online:
                    delivered_event = {
                        "type": "delivered",
                        "conversation_id": conversation_id,
                        "message_id": message.id,
                        "to": recipient_id,
                    }
                    await manager.send_to_user(recipient_id, delivered_event)
                else:
                    title = "New message"
                    body = content if len(content) < 200 else content[:197] + "..."
                    payload = {
                        "conversation_id": conversation_id,
                        "message_id": message.id,
                    }
                    asyncio.create_task(
                        asyncio.to_thread(
                            dispatch_notification, recipient_id, title, body, payload
                        )
                    )

            elif msg_type == "read":
                # Mark messages as read
                conversation_id = data.get("conversation_id")
                message_ids = data.get("message_ids", [])

                if not conversation_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "conversation_id is required for read",
                        }
                    )
                    continue

                try:
                    conversation_id = int(conversation_id)
                except (ValueError, TypeError):
                    await websocket.send_json(
                        {"type": "error", "message": "invalid conversation_id"}
                    )
                    continue

                # Verify user is subscribed to this conversation
                if (
                    websocket not in manager.subscriptions
                    or conversation_id not in manager.subscriptions[websocket]
                ):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "not_subscribed_to_conversation",
                            "conversation_id": conversation_id,
                        }
                    )
                    continue

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

                    read_event = {
                        "type": "read_receipt",
                        "message_ids": message_ids,
                        "conversation_id": conversation_id,
                        "by": user["id"],
                    }
                    await manager.send_to_conversation(conversation_id, read_event)

            # other types can be added: typing, seen, etc.

    except Exception:
        # Swallow all exceptions so nothing propagates to the framework. If we re-raise, the
        # framework sends an HTTP error response on the WebSocket scope -> RuntimeError.
        pass
    finally:
        # Always run cleanup on exit (disconnect, break, or any exception). Never raise from here.
        try:
            user_id = manager.websocket_to_user.get(websocket)
            manager.disconnect_multi(websocket)
            try:
                AuditLogService().create_log(
                    db=db,
                    action="chat.ws_disconnect_multi",
                    resource_type="chat",
                    resource_id=None,
                    user_id=user_id,
                    status="success",
                    status_code=1000,
                )
            except Exception:
                pass
        except Exception:
            pass
