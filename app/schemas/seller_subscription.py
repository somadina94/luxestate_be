from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.seller_subscription_plan import SubscriptionPlanDurationType


class SubscriptionPlanBase(BaseModel):
    name: str
    description: str
    price: float
    currency: str
    duration: int
    duration_type: SubscriptionPlanDurationType


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanUpdate(SubscriptionPlanBase):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    duration: Optional[int] = None
    duration_type: Optional[SubscriptionPlanDurationType] = None
