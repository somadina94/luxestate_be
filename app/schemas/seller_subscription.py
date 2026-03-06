from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.seller_subscription_plan import SubscriptionPlanDurationType


class SubscriptionPlanBase(BaseModel):
    name: str
    description: str
    price: float
    currency: str
    duration: int
    duration_type: SubscriptionPlanDurationType
    listing_limit: int = Field(default=30, description="Max listings for subscribers on this plan")


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    listing_limit: int = Field(default=30, description="Max listings for subscribers on this plan")
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "required": ["id", "name", "description", "price", "currency", "duration", "duration_type", "listing_limit", "created_at"],
        },
    )


class SubscriptionPlanUpdate(SubscriptionPlanBase):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    duration: Optional[int] = None
    duration_type: Optional[SubscriptionPlanDurationType] = None
    listing_limit: Optional[int] = None
