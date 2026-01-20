from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.models.property import PropertyType, PropertyStatus, ListingType


class PropertySearchParams(BaseModel):
    """Schema for property search parameters."""

    # Location filters
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    overview_image: Optional[str] = None

    # Price filters
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)

    # Property details
    property_type: Optional[PropertyType] = None
    listing_type: Optional[ListingType] = None
    status: Optional[PropertyStatus] = None
    min_bedrooms: Optional[int] = Field(None, ge=0)
    max_bedrooms: Optional[int] = Field(None, ge=0)
    min_bathrooms: Optional[float] = Field(None, ge=0)
    max_bathrooms: Optional[float] = Field(None, ge=0)
    min_square_feet: Optional[int] = Field(None, ge=0)
    max_square_feet: Optional[int] = Field(None, ge=0)
    min_lot_size: Optional[float] = Field(None, ge=0)
    max_lot_size: Optional[float] = Field(None, ge=0)
    min_year_built: Optional[int] = Field(None, ge=1800, le=2024)
    max_year_built: Optional[int] = Field(None, ge=1800, le=2024)

    # Features and amenities
    features: Optional[List[str]] = None
    amenities: Optional[List[str]] = None

    # Text search
    search_query: Optional[str] = None

    # Special filters
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None

    # Pagination
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

    # Sorting
    sort_by: str = Field(
        "created_at",
        pattern="^(created_at|updated_at|price|title|bedrooms|bathrooms|square_feet)$",
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


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
    listing_type: ListingType
    overview_image: Optional[str] = None


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
    listing_type: Optional[ListingType] = None
    overview_image: Optional[str] = None


class PropertyResponse(PropertyBase):
    id: int
    status: PropertyStatus
    agent_id: int
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    listing_type: ListingType
    overview_image: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PropertyLocationResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: float
    currency: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    latitude: float
    longitude: float
    property_type: str
    status: str
    bedrooms: int
    bathrooms: float
    square_feet: int
    lot_size: float
    year_built: int
    features: list[str]
    amenities: list[str]
    agent_id: int
    is_featured: bool
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    distance: float  # ✅ include computed field
    listing_type: ListingType
    model_config = ConfigDict(from_attributes=True)
