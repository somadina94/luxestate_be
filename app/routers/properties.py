from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Annotated, List, Optional

from sqlalchemy.orm import Session
from starlette import status
from app.database import SessionLocal
from app.models.user import User
from app.models.property import PropertyType, PropertyStatus
from app.schemas.property import (
    PropertyCreate,
    PropertyLocationResponse,
    PropertyUpdate,
    PropertyResponse,
    PropertySearchParams,
)

from app.dependencies import (
    get_current_user,
    require_permission,
    Permission,
    require_subscription,
)
from app.services.property_service import PropertyService
from app.models.subscription import SubscriptionStatus
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/properties", tags=["properties"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[
    dict, Depends(require_permission(Permission.CREATE_PROPERTIES))
]
subscription_dependency = Annotated[
    dict, Depends(require_subscription(SubscriptionStatus.PAID))
]


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    db: db_dependency,
    property: PropertyCreate,
    current_user: subscription_dependency,
    request: Request,
):
    result = await PropertyService().create_property(
        db=db, property_data=property, agent_id=current_user.get("id")
    )
    AuditLogService().create_log(
        db=db,
        action="property.create",
        resource_type="property",
        resource_id=getattr(result, "id", None),
        user_id=current_user.get("id"),
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result


@router.get("/", status_code=status.HTTP_200_OK)
async def get_properties(db: db_dependency):
    return await PropertyService().get_properties(db)


# ==================== SEARCH ENDPOINTS ====================


@router.get("/search", response_model=List[PropertyResponse])
async def search_properties(
    db: db_dependency,
    # Location filters
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    state: Optional[str] = Query(None, description="Filter by state (partial match)"),
    country: Optional[str] = Query(
        None, description="Filter by country (partial match)"
    ),
    zip_code: Optional[str] = Query(None, description="Filter by exact zip code"),
    # Price filters
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    currency: Optional[str] = Query(None, description="Currency code (e.g., USD)"),
    # Property details
    property_type: Optional[PropertyType] = Query(None, description="Type of property"),
    status: Optional[PropertyStatus] = Query(None, description="Property status"),
    min_bedrooms: Optional[int] = Query(None, description="Minimum number of bedrooms"),
    max_bedrooms: Optional[int] = Query(None, description="Maximum number of bedrooms"),
    min_bathrooms: Optional[float] = Query(
        None, description="Minimum number of bathrooms"
    ),
    max_bathrooms: Optional[float] = Query(
        None, description="Maximum number of bathrooms"
    ),
    min_square_feet: Optional[int] = Query(None, description="Minimum square footage"),
    max_square_feet: Optional[int] = Query(None, description="Maximum square footage"),
    min_lot_size: Optional[float] = Query(None, description="Minimum lot size"),
    max_lot_size: Optional[float] = Query(None, description="Maximum lot size"),
    min_year_built: Optional[int] = Query(None, description="Minimum year built"),
    max_year_built: Optional[int] = Query(None, description="Maximum year built"),
    # Features and amenities
    features: Optional[List[str]] = Query(
        None, description="Required features (e.g., pool, garage)"
    ),
    amenities: Optional[List[str]] = Query(
        None, description="Required amenities (e.g., gym, concierge)"
    ),
    # Text search
    search_query: Optional[str] = Query(
        None, description="Search in title and description"
    ),
    # Special filters
    is_featured: Optional[bool] = Query(None, description="Filter featured properties"),
    is_active: Optional[bool] = Query(None, description="Filter active properties"),
    # Pagination
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    # Sorting
    sort_by: str = Query(
        "created_at",
        pattern="^(created_at|updated_at|price|title|bedrooms|bathrooms|square_feet)$",
        description="Field to sort by",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
):
    """
    Comprehensive property search with multiple filter options.

    This endpoint allows you to search for properties using various filters including:
    - Location (city, state, country, zip code)
    - Price range and currency
    - Property details (type, bedrooms, bathrooms, square footage, etc.)
    - Features and amenities
    - Text search in title and description
    - Special filters (featured, active status)

    All filters are optional and can be combined for precise searches.
    """
    return await PropertyService().search_properties(
        db=db,
        city=city,
        state=state,
        country=country,
        zip_code=zip_code,
        min_price=min_price,
        max_price=max_price,
        currency=currency,
        property_type=property_type,
        status=status,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
        min_bathrooms=min_bathrooms,
        max_bathrooms=max_bathrooms,
        min_square_feet=min_square_feet,
        max_square_feet=max_square_feet,
        min_lot_size=min_lot_size,
        max_lot_size=max_lot_size,
        min_year_built=min_year_built,
        max_year_built=max_year_built,
        features=features,
        amenities=amenities,
        search_query=search_query,
        is_featured=is_featured,
        is_active=is_active,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/search", response_model=List[PropertyResponse])
async def search_properties_with_body(
    db: db_dependency, search_params: PropertySearchParams
):
    """
    Search properties using a request body with search parameters.

    This endpoint accepts a JSON body with all search parameters,
    which is useful for complex searches or when you have many parameters.
    """
    return await PropertyService().search_properties_with_params(
        db=db, search_params=search_params
    )


@router.get("/search/location", response_model=List[PropertyLocationResponse])
async def search_properties_by_location(
    db: db_dependency,
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    radius_km: float = Query(
        10.0, ge=0.1, le=1000, description="Search radius in kilometers"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of properties to return"
    ),
):
    """
    Find properties within a specified radius of given coordinates.

    Uses the Haversine formula to calculate distances and returns properties
    sorted by distance from the specified location.
    """
    return await PropertyService().get_properties_by_location(
        db=db, latitude=latitude, longitude=longitude, radius_km=radius_km, limit=limit
    )


@router.get("/featured", response_model=List[PropertyResponse])
async def get_featured_properties(
    db: db_dependency,
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of featured properties to return"
    ),
):
    """
    Get featured properties for homepage display.

    Returns properties that are marked as featured, active, and available.
    """
    return await PropertyService().get_featured_properties(db=db, limit=limit)


@router.get("/agent/{agent_id}", response_model=List[PropertyResponse])
async def get_properties_by_agent(
    db: db_dependency,
    agent_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
):
    """
    Get all properties for a specific agent.

    Returns all properties created by the specified agent, ordered by creation date.
    """
    return await PropertyService().get_properties_by_agent(
        db=db, agent_id=agent_id, skip=skip, limit=limit
    )


@router.get("/{property_id}", status_code=status.HTTP_200_OK)
async def get_property(db: db_dependency, property_id: int):
    return await PropertyService().get_property(db, property_id)


@router.patch("/{property_id}", status_code=status.HTTP_200_OK)
async def update_property(
    db: db_dependency,
    property: PropertyUpdate,
    user: user_dependency,
    property_id: int,
    request: Request,
):
    result = await PropertyService().update_property(
        db, property_id, property, user.get("id")
    )
    AuditLogService().create_log(
        db=db,
        action="property.update",
        resource_type="property",
        resource_id=property_id,
        user_id=user.get("id"),
        changes=property.model_dump(exclude_unset=True),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    db: db_dependency, user: user_dependency, property_id: int, request: Request
):
    result = await PropertyService().delete_property(db, property_id, user.get("id"))
    AuditLogService().create_log(
        db=db,
        action="property.delete",
        resource_type="property",
        resource_id=property_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_204_NO_CONTENT,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result
