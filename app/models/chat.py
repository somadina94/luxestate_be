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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    agent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    property_id = Column(Integer, nullable=True)
    type = Column(String, default="user-agent")  # user-agent | support

    # Snapshot names and property title for display without joins
    user_first_name = Column(String(100), nullable=True)
    user_last_name = Column(String(100), nullable=True)
    agent_first_name = Column(String(100), nullable=True)
    agent_last_name = Column(String(100), nullable=True)
    property_title = Column(String(500), nullable=True)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content = Column(Text)
    timestamp = Column(DateTime, default=utc_now)
    is_read = Column(Boolean, default=False)
    conversation = relationship("Conversation", back_populates="messages")
