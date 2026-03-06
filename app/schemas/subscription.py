from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional
from app.models.subscription import SubscriptionStatus


class SubscriptionBase(BaseModel):
    user_id: int
    subscription_plan_id: int
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    listing_limit: int = Field(default=30, description="Maximum number of listings allowed for this subscription")


class SubscriptionCreate(SubscriptionBase):
    """Create a subscription; listing_limit defaults to 30 if omitted."""

    listing_limit: int = Field(default=30, description="Max listings for this subscription; default 30")


class SubscriptionUpdate(BaseModel):
    user_id: Optional[int] = None
    subscription_plan_id: Optional[int] = None
    status: Optional[SubscriptionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    listing_limit: Optional[int] = None


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    subscription_plan_id: int
    status: str
    start_date: datetime
    end_date: datetime
    listing_limit: int = Field(default=30, description="Maximum number of listings allowed")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @model_validator(mode="before")
    @classmethod
    def ensure_listing_limit(cls, data):
        """Ensure listing_limit is always present when building from ORM/dict (e.g. old rows or mocks)."""
        if isinstance(data, dict):
            data.setdefault("listing_limit", 30)
            return data
        if hasattr(data, "__dict__"):
            if not hasattr(data, "listing_limit") or getattr(data, "listing_limit", None) is None:
                setattr(data, "listing_limit", 30)
        return data
