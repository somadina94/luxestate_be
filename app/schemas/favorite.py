from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class FavoriteBase(BaseModel):
    property_id: int


class FavoriteCreate(FavoriteBase):
    pass


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    property_id: int
    overview_image: Optional[str] = None
    address: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    year_built: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
