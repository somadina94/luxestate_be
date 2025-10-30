from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.subscription import SubscriptionStatus


class SubscriptionBase(BaseModel):
    user_id: int
    subscription_plan_id: int
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    user_id: Optional[int] = None
    subscription_plan_id: Optional[int] = None
    status: Optional[SubscriptionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SubscriptionResponse(SubscriptionBase):
    id: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True
