from sqlalchemy import select, and_, or_, func
from app.database import SessionLocal
from app.models.property import Property, PropertyStatus, PropertyType
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertySearchParams
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime


class PropertyService:
    async def create_property(
        self, db: Session, property_data: PropertyCreate, agent_id: int
    ):
        # Create a new property instance
        new_property = Property(**property_data.model_dump(), agent_id=agent_id)

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
        update_data = property_data.model_dump(exclude_unset=True)
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

    async def search_properties(
        self,
        db: Session,
        # Location filters
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        # Price filters
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        currency: Optional[str] = None,
        # Property details
        property_type: Optional[PropertyType] = None,
        status: Optional[PropertyStatus] = None,
        min_bedrooms: Optional[int] = None,
        max_bedrooms: Optional[int] = None,
        min_bathrooms: Optional[float] = None,
        max_bathrooms: Optional[float] = None,
        min_square_feet: Optional[int] = None,
        max_square_feet: Optional[int] = None,
        min_lot_size: Optional[float] = None,
        max_lot_size: Optional[float] = None,
        min_year_built: Optional[int] = None,
        max_year_built: Optional[int] = None,
        # Features and amenities
        features: Optional[List[str]] = None,
        amenities: Optional[List[str]] = None,
        # Text search
        search_query: Optional[str] = None,
        # Special filters
        is_featured: Optional[bool] = None,
        is_active: Optional[bool] = None,
        # Pagination
        skip: int = 0,
        limit: int = 100,
        # Sorting
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        """
        Comprehensive property search with multiple filter options.

        Args:
            db: Database session
            city, state, country, zip_code: Location filters
            min_price, max_price, currency: Price range filters
            property_type, status: Property type and status filters
            min_bedrooms, max_bedrooms: Bedroom count range
            min_bathrooms, max_bathrooms: Bathroom count range
            min_square_feet, max_square_feet: Square footage range
            min_lot_size, max_lot_size: Lot size range
            min_year_built, max_year_built: Year built range
            features, amenities: Lists of features/amenities to filter by
            search_query: Text search in title and description
            is_featured, is_active: Boolean filters
            skip, limit: Pagination parameters
            sort_by: Field to sort by (default: created_at)
            sort_order: Sort order (asc/desc, default: desc)
        """

        # Start with base query
        query = select(Property)

        # Build filter conditions
        conditions = []

        # Location filters
        if city:
            conditions.append(func.lower(Property.city).contains(func.lower(city)))
        if state:
            conditions.append(func.lower(Property.state).contains(func.lower(state)))
        if country:
            conditions.append(
                func.lower(Property.country).contains(func.lower(country))
            )
        if zip_code:
            conditions.append(Property.zip_code == zip_code)

        # Price filters
        if min_price is not None:
            conditions.append(Property.price >= min_price)
        if max_price is not None:
            conditions.append(Property.price <= max_price)
        if currency:
            conditions.append(Property.currency == currency.upper())

        # Property details
        if property_type:
            conditions.append(Property.property_type == property_type)
        if status:
            conditions.append(Property.status == status)

        # Bedroom filters
        if min_bedrooms is not None:
            conditions.append(Property.bedrooms >= min_bedrooms)
        if max_bedrooms is not None:
            conditions.append(Property.bedrooms <= max_bedrooms)

        # Bathroom filters
        if min_bathrooms is not None:
            conditions.append(Property.bathrooms >= min_bathrooms)
        if max_bathrooms is not None:
            conditions.append(Property.bathrooms <= max_bathrooms)

        # Square footage filters
        if min_square_feet is not None:
            conditions.append(Property.square_feet >= min_square_feet)
        if max_square_feet is not None:
            conditions.append(Property.square_feet <= max_square_feet)

        # Lot size filters
        if min_lot_size is not None:
            conditions.append(Property.lot_size >= min_lot_size)
        if max_lot_size is not None:
            conditions.append(Property.lot_size <= max_lot_size)

        # Year built filters
        if min_year_built is not None:
            conditions.append(Property.year_built >= min_year_built)
        if max_year_built is not None:
            conditions.append(Property.year_built <= max_year_built)

        # Features filter (JSON contains)
        if features:
            for feature in features:
                conditions.append(Property.features.contains([feature]))

        # Amenities filter (JSON contains)
        if amenities:
            for amenity in amenities:
                conditions.append(Property.amenities.contains([amenity]))

        # Text search in title and description
        if search_query:
            search_conditions = [
                func.lower(Property.title).contains(func.lower(search_query)),
                func.lower(Property.description).contains(func.lower(search_query)),
            ]
            conditions.append(or_(*search_conditions))

        # Special filters
        if is_featured is not None:
            conditions.append(Property.is_featured == is_featured)
        if is_active is not None:
            conditions.append(Property.is_active == is_active)

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Sorting
        sort_column = getattr(Property, sort_by, Property.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = db.execute(query)
        properties = result.scalars().all()

        return properties

    async def search_properties_with_params(
        self, db: Session, search_params: PropertySearchParams
    ):
        """
        Search properties using PropertySearchParams schema.
        This is a convenience method that unpacks the search parameters.
        """
        return await self.search_properties(
            db=db,
            city=search_params.city,
            state=search_params.state,
            country=search_params.country,
            zip_code=search_params.zip_code,
            min_price=search_params.min_price,
            max_price=search_params.max_price,
            currency=search_params.currency,
            property_type=search_params.property_type,
            status=search_params.status,
            min_bedrooms=search_params.min_bedrooms,
            max_bedrooms=search_params.max_bedrooms,
            min_bathrooms=search_params.min_bathrooms,
            max_bathrooms=search_params.max_bathrooms,
            min_square_feet=search_params.min_square_feet,
            max_square_feet=search_params.max_square_feet,
            min_lot_size=search_params.min_lot_size,
            max_lot_size=search_params.max_lot_size,
            min_year_built=search_params.min_year_built,
            max_year_built=search_params.max_year_built,
            features=search_params.features,
            amenities=search_params.amenities,
            search_query=search_params.search_query,
            is_featured=search_params.is_featured,
            is_active=search_params.is_active,
            skip=search_params.skip,
            limit=search_params.limit,
            sort_by=search_params.sort_by,
            sort_order=search_params.sort_order,
        )

    async def get_properties_by_location(
        self,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        limit: int = 50,
    ):
        """


        Find properties within a certain radius of given coordinates.
        Uses Haversine formula for distance calculation.


        """
        EARTH_RADIUS = 6371  # km

        distance_formula = EARTH_RADIUS * func.acos(
            func.cos(func.radians(latitude))
            * func.cos(func.radians(Property.latitude))
            * func.cos(func.radians(Property.longitude) - func.radians(longitude))
            + func.sin(func.radians(latitude))
            * func.sin(func.radians(Property.latitude))
        )

        # ✅ Subquery to compute distance first
        subquery = (
            select(
                Property.id,
                Property.title,
                Property.description,
                Property.price,
                Property.currency,
                Property.address,
                Property.city,
                Property.state,
                Property.zip_code,
                Property.country,
                Property.latitude,
                Property.longitude,
                Property.property_type,
                Property.status,
                Property.bedrooms,
                Property.bathrooms,
                Property.square_feet,
                Property.lot_size,
                Property.year_built,
                Property.features,
                Property.amenities,
                Property.agent_id,
                Property.is_featured,
                Property.is_active,
                Property.created_at,
                Property.updated_at,
                distance_formula.label("distance"),
            )
            .where(
                and_(
                    Property.latitude.isnot(None),
                    Property.longitude.isnot(None),
                    Property.is_active == True,
                )
            )
            .subquery()
        )

        # ✅ Now we can filter using WHERE
        query = (
            select(subquery)
            .where(subquery.c.distance <= radius_km)
            .order_by(subquery.c.distance)
            .limit(limit)
        )

        result = db.execute(query)
        return result.all()

    async def get_featured_properties(self, db: Session, limit: int = 10):
        """Get featured properties for homepage display."""
        query = (
            select(Property)
            .where(
                and_(
                    Property.is_featured == True,
                    Property.is_active == True,
                    Property.status == PropertyStatus.AVAILABLE,
                )
            )
            .order_by(Property.created_at.desc())
            .limit(limit)
        )

        result = db.execute(query)
        return result.scalars().all()

    async def get_properties_by_agent(
        self, db: Session, agent_id: int, skip: int = 0, limit: int = 100
    ):
        """Get all properties for a specific agent."""
        query = (
            select(Property)
            .where(Property.agent_id == agent_id)
            .order_by(Property.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = db.execute(query)
        return result.scalars().all()
