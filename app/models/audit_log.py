from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # Actor information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String, nullable=True)  # Denormalized for queries
    user_role = Column(String, nullable=True)  # Denormalized for quick filtering
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Action details
    action = Column(
        String, nullable=False, index=True
    )  # e.g., "create", "update", "delete", "login"
    resource_type = Column(
        String, nullable=False, index=True
    )  # e.g., "property", "user", "subscription"
    resource_id = Column(Integer, nullable=True, index=True)

    # Changes tracking (for updates)
    changes = Column(JSON, nullable=True)  # {field: {"old": value, "new": value}}
    before_state = Column(JSON, nullable=True)  # Full resource state before change
    after_state = Column(JSON, nullable=True)  # Full resource state after change

    # Request context
    request_method = Column(String, nullable=True)  # GET, POST, PATCH, DELETE
    request_path = Column(String, nullable=True)  # e.g., "/properties/123"
    request_body_hash = Column(
        String, nullable=True
    )  # SHA256 hash of request body (if sensitive)

    # Outcome
    status = Column(String, nullable=False, index=True)  # "success", "failure", "error"
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_ms = Column(Integer, nullable=True)  # Request processing time

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
