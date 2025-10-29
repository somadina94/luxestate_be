from pydantic import BaseModel
from typing import Optional


class StripeCheckoutCreate(BaseModel):
    subscription_plan_id: int


class StripeCheckoutResponse(BaseModel):
    session_id: str
    url: str
