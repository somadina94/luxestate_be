from pydantic import BaseModel
from datetime import datetime
from app.models.subscription import SubscriptionStatus


class SubscriptionBase(BaseModel):
    user_id: int
    subscription_plan_id: int
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    created_at: datetime
    updated_at: datetime


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(SubscriptionBase):
    pass


class SubscriptionResponse(SubscriptionBase):
    id: int

    class Config:
        from_attributes = True
