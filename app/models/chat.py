from sqlalchemy import Boolean, Column, Integer, ForeignKey, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def utc_now():
    """Return current UTC timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    property_id = Column(Integer, nullable=True)
    type = Column(String, default="user-agent")  # user-agent | support

    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    timestamp = Column(DateTime, default=utc_now)
    is_read = Column(Boolean, default=False)
    conversation = relationship("Conversation", back_populates="messages")
