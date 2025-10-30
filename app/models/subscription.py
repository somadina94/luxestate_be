from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    Enum as SqlEnum,
)
from app.database import Base
from sqlalchemy.sql import func
import enum


class SubscriptionStatus(str, enum.Enum):
    EXPIRED = "expired"
    PAID = "paid"
    CANCELLED = "cancelled"


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(
        SqlEnum(
            SubscriptionStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
        ),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
