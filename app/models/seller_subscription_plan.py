from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Enum as SqlEnum
from app.database import Base
from sqlalchemy.sql import func
import enum


class SubscriptionPlanDurationType(str, enum.Enum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    duration = Column(Integer, nullable=False)
    duration_type = Column(SqlEnum(SubscriptionPlanDurationType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
