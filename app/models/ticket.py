from datetime import datetime, timezone
import enum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    """Return current UTC timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=utc_now)
    messages = relationship(
        "TicketMessage", back_populates="ticket", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="tickets")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    ticket = relationship("Ticket", back_populates="messages")
