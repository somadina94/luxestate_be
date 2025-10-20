from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.property import PropertyType, PropertyStatus


class PropertyBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    address: str = Field(..., max_length=500)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    zip_code: str = Field(..., max_length=20)
    country: str = Field(default="USA", max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: PropertyType
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[float] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, gt=0)
    lot_size: Optional[float] = Field(None, gt=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2024)
    features: Optional[List[str]] = None
    amenities: Optional[List[str]] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    status: Optional[PropertyStatus] = None
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[float] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, gt=0)
    features: Optional[List[str]] = None
    amenities: Optional[List[str]] = None


class PropertyResponse(PropertyBase):
    id: int
    status: PropertyStatus
    agent_id: int
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
