from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ListingType(str, enum.Enum):
    SALE = "sale"
    RENT = "rent"
    LEASE = "lease"


class PropertyType(str, enum.Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    VILLA = "villa"
    PENTHOUSE = "penthouse"
    STUDIO = "studio"


class PropertyStatus(str, enum.Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    SOLD = "sold"
    RENTED = "rented"
    OFF_MARKET = "off_market"


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")

    # Location
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    zip_code = Column(String(20), nullable=False)
    country = Column(String(100), default="USA")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Property Details
    property_type = Column(Enum(PropertyType), nullable=False)
    status = Column(Enum(PropertyStatus), default=PropertyStatus.AVAILABLE)
    listing_type = Column(Enum(ListingType), nullable=False)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)
    square_feet = Column(Integer, nullable=True)
    lot_size = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)

    # Features & Amenities
    features = Column(JSON, nullable=True)  # ["pool", "garage", "garden"]
    amenities = Column(JSON, nullable=True)  # ["gym", "concierge", "parking"]

    # Agent/Owner
    agent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Metadata
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    agent = relationship("User", back_populates="properties")
    images = relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan"
    )
    favorites = relationship("Favorite", back_populates="property")
