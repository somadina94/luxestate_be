from sqlalchemy import select, and_
from app.database import SessionLocal
from app.models.property import Property, PropertyStatus
from app.schemas.property import PropertyCreate, PropertyUpdate
from sqlalchemy.orm import Session

from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List

from app.models.property import Property  # Your SQLAlchemy model
from app.schemas.property import PropertyCreate, PropertyUpdate  # Your Pydantic schemas


class PropertyService:
    async def create_property(
        self, db: Session, property_data: PropertyCreate, agent_id: int
    ):
        # Create a new property instance
        new_property = Property(**property_data.dict(), agent_id=agent_id)

        db.add(new_property)
        db.commit()
        db.refresh(new_property)  # Return object with ID populated

        return new_property

    async def get_properties(self, db: Session, skip: int = 0, limit: int = 100):
        result = db.execute(select(Property).offset(skip).limit(limit))
        return result.scalars().all()

    async def get_property(self, db: Session, property_id: int):
        result = db.execute(select(Property).where(Property.id == property_id))
        property = result.scalar_one_or_none()

        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with ID {property_id} not found",
            )
        return property

    async def update_property(
        self,
        db: Session,
        property_id: int,
        property_data: PropertyUpdate,
        user_id: int,
    ):
        # Fetch property
        result = db.execute(select(Property).where(Property.id == property_id))
        property = result.scalar_one_or_none()

        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with ID {property_id} not found",
            )

        # Authorization check
        if property.agent_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this property",
            )

        # Update fields selectively
        update_data = property_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(property, key, value)

        db.commit()
        db.refresh(property)

        return property

    async def delete_property(self, db: Session, property_id: int, user_id: int):
        result = db.execute(select(Property).where(Property.id == property_id))
        property = result.scalar_one_or_none()

        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with ID {property_id} not found",
            )

        if property.agent_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this property",
            )

        db.delete(property)
        db.commit()

        return {"detail": "Property deleted successfully"}
