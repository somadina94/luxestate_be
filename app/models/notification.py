from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base  # adapt import


def utc_now():
    """Return current UTC timezone-aware datetime."""
    return datetime.now(timezone.utc)


class UserPushToken(Base):
    __tablename__ = "user_push_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    expo_token = Column(String, nullable=True)  # ExponentPushToken[...] (mobile)
    web_push_subscription = Column(Text, nullable=True)  # JSON string of subscription
    updated_at = Column(DateTime, default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    body = Column(Text)
    payload = Column(Text, nullable=True)  # JSON payload string
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
