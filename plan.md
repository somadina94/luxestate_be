# LuxeState Backend Development Plan

## Table of Contents

- [Phase 0: Planning & Foundations](#phase-0--planning--foundations)
- [Phase 1: Project Scaffolding & Core Plumbing](#phase-1--project-scaffolding--core-plumbing)
- [Phase 2: Authentication & User Management](#phase-2--authentication--user-management)
- [Phase 3: Core Listings Functionality](#phase-3--core-listings-functionality)
- [Phase 4: Search, Filters, and Discovery](#phase-4--search-filters-and-discovery)
- [Phase 5: User Features and Interactions](#phase-5--user-features-and-interactions)
- [Phase 6: Payments, Plans & Monetization](#phase-6--payments-plans--monetization)
- [Phase 7: Admin & Moderation](#phase-7--admin--moderation)
- [Phase 8: Performance, Reliability & Security](#phase-8--performance-reliability--security)
- [Phase 9: Testing Strategy](#phase-9--testing-strategy)
- [Phase 10: Documentation, Developer Ergonomics & Release](#phase-10--documentation-developer-ergonomics--release)
- [Acceptance Checklist](#acceptance-checklist)
- [Testing Priorities](#testing-priorities)
- [Extras & Nice-to-Have](#extras--nice-to-have)

---

## Phase 0 — Planning & Foundations

### 1. Define Requirements & Actors

**Purpose:** Decide user roles, core features, and required flows.

**Step-by-Step Actions:**

1. **Define User Roles:**

   - `GUEST` - Browse properties, view details
   - `BUYER/RENTER` - Register, save favorites, contact agents
   - `OWNER/AGENT` - Create listings, manage properties, respond to inquiries
   - `ADMIN` - Manage users, moderate content, view analytics

2. **List Core Features:**
   - User authentication & authorization
   - Property CRUD operations
   - Advanced search & filtering
   - Image upload & management
   - Contact/inquiry system
   - Favorites/bookmarks
   - Payment processing (optional)
   - Admin dashboard

**Deliverables:**

- User roles specification document
- Feature requirements list
- User journey maps

**Tests:** None yet — acceptance = spec approved.

### 2. Data Model & API Surface Sketch

**Purpose:** Sketch primary entities and key endpoints (high level).

**Step-by-Step Actions:**

1. **Create ER Diagram** with these core models:

   - `User` (id, email, password_hash, role, created_at, updated_at, is_active)
   - `Property` (id, title, description, price, location, type, status, agent_id, created_at)
   - `PropertyImage` (id, property_id, file_key, is_primary, order_index)
   - `Favorite` (id, user_id, property_id, created_at)
   - `Message` (id, sender_id, recipient_id, property_id, content, created_at)
   - `AgentProfile` (id, user_id, license_number, verification_status, bio)
   - `Subscription` (id, user_id, plan_id, status, expires_at)
   - `AuditLog` (id, user_id, action, resource_type, resource_id, timestamp)

2. **Define API Endpoints** (high-level):
   - Authentication: `/auth/*`
   - Properties: `/properties/*`
   - Users: `/users/*`
   - Admin: `/admin/*`

**Deliverables:**

- ER diagram (using draw.io or similar)
- API endpoint list
- Model relationships documentation

**Acceptance:** Endpoints & models cover every requirement.

### 3. Decide Tech Choices & Infrastructure

**Purpose:** Lock stack details relevant to backend (DB, auth method, storage).

**Step-by-Step Actions:**

1. **Backend Framework:** FastAPI (async, auto-docs, type hints)
2. **Database:** SQLite (local development, easy setup, upgrade to PostgreSQL later)
3. **ORM:** SQLAlchemy 2.0+ with async support
4. **Migrations:** Alembic
5. **Authentication:** JWT tokens with refresh mechanism
6. **File Storage:** Local file system (upgrade to S3 later)
7. **Background Tasks:** FastAPI BackgroundTasks (upgrade to Celery later)
8. **Caching:** In-memory (upgrade to Redis later)
9. **Testing:** pytest + pytest-asyncio + httpx
10. **Deployment:** Docker + Docker Compose

**Deliverables:**

- Technology stack document
- Architecture diagram
- Development environment setup guide

**Acceptance:** Clear list of libraries and infra to use.

## Phase 1 — Project Scaffolding & Core Plumbing

### 1. Project Skeleton

**Purpose:** Create folder structure, main app, configurations (envs).

**Step-by-Step Actions:**

1. **Create Project Structure:**

   ```
   luxestate_be/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── config.py
   │   ├── database.py
   │   ├── dependencies.py
   │   ├── models/
   │   │   ├── __init__.py
   │   │   ├── user.py
   │   │   └── property.py
   │   ├── schemas/
   │   │   ├── __init__.py
   │   │   ├── user.py
   │   │   └── property.py
   │   ├── routers/
   │   │   ├── __init__.py
   │   │   ├── auth.py
   │   │   └── properties.py
   │   ├── services/
   │   │   ├── __init__.py
   │   │   ├── auth_service.py
   │   │   └── property_service.py
   │   └── tests/
   │       ├── __init__.py
   │       ├── conftest.py
   │       └── test_auth.py
   ├── alembic/
   ├── requirements.txt
   ├── .env.example
   └── docker-compose.yml
   ```

2. **Initialize FastAPI App:**

   - Create `app/main.py` with basic FastAPI instance
   - Add health check endpoint
   - Configure CORS middleware

3. **Setup Virtual Environment:**
   - Create virtual environment
   - Install FastAPI, SQLAlchemy, Alembic, pytest

**Deliverables:**

- Complete project structure
- Working FastAPI app with health endpoint
- Virtual environment with dependencies

**Acceptance:** App starts and returns a health endpoint.

### 2. Configuration & Environment

**Purpose:** Centralized config for DB, secrets, S3, JWT, CORS.

**Step-by-Step Actions:**

1. **Create Config Module (`app/config.py`):**

   ```python
   from pydantic_settings import BaseSettings

   class Settings(BaseSettings):
       # Database
       DATABASE_URL: str = "sqlite:///./luxestate.db"

       # JWT
       SECRET_KEY: str
       ALGORITHM: str = "HS256"
       ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

       # File Storage (Local)
       UPLOAD_DIR: str = "./uploads"

       class Config:
           env_file = ".env"
   ```

2. **Create `.env.example`:**

   ```
   DATABASE_URL=sqlite:///./luxestate.db
   SECRET_KEY=your-secret-key-here
   UPLOAD_DIR=./uploads
   ```

3. **Add Environment Validation:**
   - Validate required environment variables
   - Provide helpful error messages for missing vars

**Deliverables:**

- Config module with validation
- `.env.example` template
- Environment variable documentation

**Tests:** Ensure config validation (e.g., missing DB raises error).

### 3. Database Connection & Migrations

**Purpose:** Connect FastAPI to DB and enable migrations.

**Step-by-Step Actions:**

1. **Setup Database Connection (`app/database.py`):**

   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker
   from app.config import settings

   engine = create_async_engine(settings.DATABASE_URL)
   AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

   async def get_db():
       async with AsyncSessionLocal() as session:
           yield session
   ```

2. **Initialize Alembic:**

   ```bash
   alembic init alembic
   ```

3. **Configure Alembic (`alembic.ini`):**

   - Set database URL
   - Configure migration directory

4. **Create Initial Migration:**

   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

5. **Setup Database Dependency:**
   - Add `get_db()` dependency to FastAPI
   - Test database connection

**Deliverables:**

- Database connection module
- Alembic configuration
- Initial migration file
- Database dependency injection

**Tests:** On CI, spin up test DB and run migrations successfully.

## Phase 2 — Authentication & User Management

### 1. User Model & Persistence

**Purpose:** Design user model (email, hashed_password, role, profile fields).

**Step-by-Step Actions:**

1. **Create User Model (`app/models/user.py`):**

   ```python
   from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
   from sqlalchemy.sql import func
   from app.database import Base
   import enum

   class UserRole(str, enum.Enum):
       GUEST = "guest"
       BUYER = "buyer"
       RENTER = "renter"
       OWNER = "owner"
       AGENT = "agent"
       ADMIN = "admin"

   class User(Base):
       __tablename__ = "users"

       id = Column(Integer, primary_key=True, index=True)
       email = Column(String, unique=True, index=True, nullable=False)
       password_hash = Column(String, nullable=False)
       role = Column(Enum(UserRole), default=UserRole.BUYER)
       first_name = Column(String, nullable=True)
       last_name = Column(String, nullable=True)
       phone = Column(String, nullable=True)
       is_active = Column(Boolean, default=True)
       is_verified = Column(Boolean, default=False)
       created_at = Column(DateTime(timezone=True), server_default=func.now())
       updated_at = Column(DateTime(timezone=True), onupdate=func.now())
   ```

2. **Create User Schemas (`app/schemas/user.py`):**

   ```python
   from pydantic import BaseModel, EmailStr
   from datetime import datetime
   from app.models.user import UserRole

   class UserBase(BaseModel):
       email: EmailStr
       first_name: str | None = None
       last_name: str | None = None
       phone: str | None = None

   class UserCreate(UserBase):
       password: str
       role: UserRole = UserRole.BUYER

   class UserResponse(UserBase):
       id: int
       role: UserRole
       is_active: bool
       is_verified: bool
       created_at: datetime

       class Config:
           from_attributes = True
   ```

3. **Create User Service (`app/services/user_service.py`):**
   - Password hashing with bcrypt
   - User creation and retrieval methods
   - Email validation

**Deliverables:**

- User model with all required fields
- User schemas for API validation
- User service with password hashing
- Database migration for User table

**Tests:** Unit tests for create/get user; password hashing logic tests.

### 2. Auth System (JWT)

**Purpose:** Registration, login, token issuance/refresh, protected endpoints.

**Step-by-Step Actions:**

1. **Create Auth Service (`app/services/auth_service.py`):**

   ```python
   from datetime import datetime, timedelta
   from jose import JWTError, jwt
   from passlib.context import CryptContext
   from app.config import settings

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)

   def get_password_hash(password: str) -> str:
       return pwd_context.hash(password)

   def create_access_token(data: dict, expires_delta: timedelta | None = None):
       to_encode = data.copy()
       if expires_delta:
           expire = datetime.utcnow() + expires_delta
       else:
           expire = datetime.utcnow() + timedelta(minutes=15)
       to_encode.update({"exp": expire})
       encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
       return encoded_jwt
   ```

2. **Create Auth Router (`app/routers/auth.py`):**

   ```python
   from fastapi import APIRouter, Depends, HTTPException, status
   from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
   from app.schemas.user import UserCreate, UserResponse
   from app.services.auth_service import authenticate_user, create_access_token

   router = APIRouter(prefix="/auth", tags=["authentication"])
   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

   @router.post("/register", response_model=UserResponse)
   async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
       # Implementation here
       pass

   @router.post("/login")
   async def login(form_data: OAuth2PasswordRequestForm = Depends()):
       # Implementation here
       pass

   @router.get("/me", response_model=UserResponse)
   async def read_users_me(current_user: User = Depends(get_current_user)):
       return current_user
   ```

3. **Create Auth Dependencies (`app/dependencies.py`):**
   - `get_current_user()` dependency
   - `get_current_active_user()` dependency
   - Role-based access control

**Deliverables / Endpoints:**

- `POST /auth/register` - User registration
- `POST /auth/login` - User login with JWT token
- `POST /auth/refresh` - Token refresh (optional)
- `GET /auth/me` - Get current user profile

**Acceptance Criteria:** Token-protected route accessible with valid token only.

**Tests:** pytest tests for registration, login (correct/incorrect credentials), token expiry handling.

### 3. Roles & Permissions

**Purpose:** Restrict actions by role (agent vs normal user vs admin).

**Step-by-Step Actions:**

1. **Create Permission System:**

   ```python
   from enum import Enum

   class Permission(str, Enum):
       READ_PROPERTIES = "read:properties"
       CREATE_PROPERTIES = "create:properties"
       UPDATE_PROPERTIES = "update:properties"
       DELETE_PROPERTIES = "delete:properties"
       MANAGE_USERS = "manage:users"
       VIEW_ANALYTICS = "view:analytics"

   ROLE_PERMISSIONS = {
       UserRole.GUEST: [Permission.READ_PROPERTIES],
       UserRole.BUYER: [Permission.READ_PROPERTIES],
       UserRole.RENTER: [Permission.READ_PROPERTIES],
       UserRole.OWNER: [Permission.READ_PROPERTIES, Permission.CREATE_PROPERTIES, Permission.UPDATE_PROPERTIES],
       UserRole.AGENT: [Permission.READ_PROPERTIES, Permission.CREATE_PROPERTIES, Permission.UPDATE_PROPERTIES],
       UserRole.ADMIN: [Permission.READ_PROPERTIES, Permission.CREATE_PROPERTIES, Permission.UPDATE_PROPERTIES, Permission.DELETE_PROPERTIES, Permission.MANAGE_USERS, Permission.VIEW_ANALYTICS]
   }
   ```

2. **Create Permission Dependencies:**
   - `require_permission()` decorator
   - Role-based endpoint protection

**Deliverables:**

- Permission system with role mappings
- Permission checking dependencies
- Protected endpoint examples

**Tests:** Protected endpoint returns 403/401 where appropriate.

## Phase 3 — Core Listings Functionality

### 1. Property Model

**Purpose:** Primary listing entity with fields like title, description, price, location (lat/lon), type, status, features, agent_id, created_at, status.

**Step-by-Step Actions:**

1. **Create Property Model (`app/models/property.py`):**

   ```python
   from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum
   from sqlalchemy.sql import func
   from sqlalchemy.orm import relationship
   from app.database import Base
   import enum

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
       bedrooms = Column(Integer, nullable=True)
       bathrooms = Column(Float, nullable=True)
       square_feet = Column(Integer, nullable=True)
       lot_size = Column(Float, nullable=True)
       year_built = Column(Integer, nullable=True)

       # Features & Amenities
       features = Column(JSON, nullable=True)  # ["pool", "garage", "garden"]
       amenities = Column(JSON, nullable=True)  # ["gym", "concierge", "parking"]

       # Agent/Owner
       agent_id = Column(Integer, ForeignKey("users.id"), nullable=False)

       # Metadata
       is_featured = Column(Boolean, default=False)
       is_active = Column(Boolean, default=True)
       created_at = Column(DateTime(timezone=True), server_default=func.now())
       updated_at = Column(DateTime(timezone=True), onupdate=func.now())

       # Relationships
       agent = relationship("User", back_populates="properties")
       images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
       favorites = relationship("Favorite", back_populates="property")
   ```

2. **Create PropertyImage Model (`app/models/property_image.py`):**

   ```python
   class PropertyImage(Base):
       __tablename__ = "property_images"

       id = Column(Integer, primary_key=True, index=True)
       property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
       file_key = Column(String(500), nullable=False)  # S3 key
       file_url = Column(String(1000), nullable=True)  # Full URL
       is_primary = Column(Boolean, default=False)
       order_index = Column(Integer, default=0)
       alt_text = Column(String(200), nullable=True)
       created_at = Column(DateTime(timezone=True), server_default=func.now())

       # Relationships
       property = relationship("Property", back_populates="images")
   ```

3. **Create Property Schemas (`app/schemas/property.py`):**

   ```python
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
   ```

**Deliverables:**

- Property model with comprehensive fields
- PropertyImage model for media management
- Property schemas for API validation
- Database migration for Property tables

**Acceptance:** Basic create/read on DB.

### 2. Property CRUD Endpoints

**Purpose:** Complete CRUD operations for properties with proper permissions.

**Step-by-Step Actions:**

1. **Create Property Service (`app/services/property_service.py`):**

   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, and_
   from app.models.property import Property, PropertyStatus
   from app.schemas.property import PropertyCreate, PropertyUpdate

   class PropertyService:
       async def create_property(self, db: AsyncSession, property_data: PropertyCreate, agent_id: int):
           # Implementation for creating property
           pass

       async def get_properties(self, db: AsyncSession, skip: int = 0, limit: int = 100):
           # Implementation for listing properties with pagination
           pass

       async def get_property(self, db: AsyncSession, property_id: int):
           # Implementation for getting single property
           pass

       async def update_property(self, db: AsyncSession, property_id: int, property_data: PropertyUpdate, user_id: int):
           # Implementation for updating property with ownership check
           pass

       async def delete_property(self, db: AsyncSession, property_id: int, user_id: int):
           # Implementation for deleting property with ownership check
           pass
   ```

2. **Create Property Router (`app/routers/properties.py`):**

   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   from typing import List, Optional
   from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
   from app.services.property_service import PropertyService
   from app.dependencies import get_current_user, require_permission

   router = APIRouter(prefix="/properties", tags=["properties"])
   property_service = PropertyService()

   @router.post("/", response_model=PropertyResponse)
   async def create_property(
       property: PropertyCreate,
       current_user: User = Depends(require_permission("create:properties")),
       db: AsyncSession = Depends(get_db)
   ):
       return await property_service.create_property(db, property, current_user.id)

   @router.get("/", response_model=List[PropertyResponse])
   async def list_properties(
       skip: int = Query(0, ge=0),
       limit: int = Query(100, ge=1, le=1000),
       city: Optional[str] = None,
       property_type: Optional[PropertyType] = None,
       min_price: Optional[float] = Query(None, ge=0),
       max_price: Optional[float] = Query(None, ge=0),
       db: AsyncSession = Depends(get_db)
   ):
       return await property_service.get_properties(db, skip, limit, city, property_type, min_price, max_price)

   @router.get("/{property_id}", response_model=PropertyResponse)
   async def get_property(property_id: int, db: AsyncSession = Depends(get_db)):
       return await property_service.get_property(db, property_id)

   @router.put("/{property_id}", response_model=PropertyResponse)
   async def update_property(
       property_id: int,
       property: PropertyUpdate,
       current_user: User = Depends(require_permission("update:properties")),
       db: AsyncSession = Depends(get_db)
   ):
       return await property_service.update_property(db, property_id, property, current_user.id)

   @router.delete("/{property_id}")
   async def delete_property(
       property_id: int,
       current_user: User = Depends(require_permission("delete:properties")),
       db: AsyncSession = Depends(get_db)
   ):
       await property_service.delete_property(db, property_id, current_user.id)
       return {"message": "Property deleted successfully"}
   ```

**Endpoints:**

- `POST /properties/` — create (agent/owner only)
- `GET /properties/` — list (filters, pagination)
- `GET /properties/{id}` — detail
- `PUT /properties/{id}` — update (owner/agent)
- `DELETE /properties/{id}` — delete (owner/agent/admin)

**Tests:**

- Unit tests for service logic (validation, ownership)
- Integration tests with TestClient for full request/response cycles

**Acceptance:** CRUD operations enforce permissions and store correct data.

### 3. Property Images / Media

**Purpose:** Allow multiple images per property, optimized storage.

**Step-by-Step Actions:**

1. **Create Image Upload Service (`app/services/image_service.py`):**

   ```python
   import os
   import uuid
   from fastapi import UploadFile
   from app.config import settings

   class ImageService:
       def __init__(self):
           self.upload_dir = settings.UPLOAD_DIR
           os.makedirs(self.upload_dir, exist_ok=True)

       async def upload_image(self, file: UploadFile, property_id: int) -> str:
           # Generate unique filename
           file_extension = file.filename.split('.')[-1]
           filename = f"{uuid.uuid4()}.{file_extension}"
           file_path = os.path.join(self.upload_dir, f"properties_{property_id}_{filename}")

           # Save file locally
           with open(file_path, "wb") as buffer:
               content = await file.read()
               buffer.write(content)

           return file_path

       async def delete_image(self, file_path: str):
           if os.path.exists(file_path):
               os.remove(file_path)
   ```

2. **Create Image Router (`app/routers/images.py`):**

   ```python
   @router.post("/properties/{property_id}/images")
   async def upload_property_image(
       property_id: int,
       file: UploadFile = File(...),
       current_user: User = Depends(require_permission("update:properties")),
       db: AsyncSession = Depends(get_db)
   ):
       # Validate file type and size
       if not file.content_type.startswith('image/'):
           raise HTTPException(status_code=400, detail="File must be an image")

       if file.size > 10 * 1024 * 1024:  # 10MB limit
           raise HTTPException(status_code=400, detail="File too large")

       # Upload image
       file_key = await image_service.upload_image(file, property_id)

       # Save to database
       image = PropertyImage(
           property_id=property_id,
           file_key=file_path,
           file_url=f"/static/{os.path.basename(file_path)}"
       )
       db.add(image)
       await db.commit()

       return {"message": "Image uploaded successfully", "file_path": file_path}

   @router.get("/media/{file_path}")
   async def get_image(file_path: str):
       # Serve local file
       if os.path.exists(file_path):
           return FileResponse(file_path)
       raise HTTPException(status_code=404, detail="Image not found")

   @router.delete("/properties/{property_id}/images/{image_id}")
   async def delete_property_image(
       property_id: int,
       image_id: int,
       current_user: User = Depends(require_permission("update:properties")),
       db: AsyncSession = Depends(get_db)
   ):
       # Delete from S3 and database
       pass
   ```

**Deliverables:**

- PropertyImage model with file_key
- Image upload service with S3 integration
- Image management endpoints
- File validation and size limits

**Tests:**

- Mock S3/storage in tests, test uploads, deletion, and DB references

## Phase 4 — Search, Filters, and Discovery

### 1. Filtering, Pagination, Sorting

**Purpose:** Provide performant listing queries and consistent paginated responses.

**Deliverables:**

- Query parameters for price range, beds, baths, type, city, bounding box (lat/lon), page, limit, sort_by

**Tests:**

- Unit tests for query-building
- Integration tests verifying results and pagination metadata

### 2. Full-text & Geospatial Search (Optional Advanced)

**Purpose:** Fast, relevant search and map-based queries.

**Deliverables:**

- Either Postgres full-text + PostGIS or an external search engine (Elasticsearch/Typesense)

**Tests:**

- Test indexed search results
- Geo queries return properties within radius

### 3. Recommendations & Related Properties (Optional)

**Purpose:** Suggested properties based on user behavior or similarity.

**Deliverables:**

- Simple rule-based recommendations to start (same area, price range) — service endpoint

**Tests:** Logic tests for matching rules.

## Phase 5 — User Features and Interactions

### 1. Favorites / Bookmarks

**Endpoints:**

- `POST /favorites/{property_id}`
- `DELETE /favorites/{property_id}`
- `GET /users/{id}/favorites`

**Deliverables:**

- Favorite model linking user and property

**Tests:** CRUD tests ensuring idempotency and ownership.

### 2. Messaging / Inquiries

**Endpoints:**

- `POST /contact/{property_id}` — send inquiry
- `GET /messages/` — inbox (agent)

**Deliverables:**

- Message model
- Email/notification hook

**Tests:**

- Message creation
- Notification sending mocked
- Inbox retrieval

### 3. Agent Profiles / Verification

**Purpose:** Profile for agents with credentials and verification status.

**Deliverables:**

- AgentProfile model
- Endpoints to claim/verify

**Tests:** Profile creation and verification flow.

## Phase 6 — Payments, Plans & Monetization (Optional)

### 1. Subscription & Payments

**Purpose:** Let agents pay for featured listings or subscriptions.

**Deliverables:**

- Plan, Subscription, Transaction models
- Endpoints for checkout webhook handling (Stripe/webhook flow)

**Tests:**

- Webhook handling tests
- DB updates on success
- Error paths

### 2. Featured/Promotion Workflow

**Purpose:** Admin/agent can promote listing for a duration.

**Deliverables:**

- Scheduled task that flips featured state or expiration logic

**Tests:**

- Background job simulation
- Expiry behavior

## Phase 7 — Admin & Moderation

### 1. Admin Panel APIs

**Endpoints:**

- List users
- Suspend/unsuspend accounts
- Moderate listings
- View payments

**Deliverables:**

- Admin-only routers
- Audit logs

**Tests:** Admin actions and audit logging.

### 2. Moderation & Content Validation

**Purpose:** Prevent spam/fraud and flagging system for users.

**Deliverables:**

- Flag endpoints
- Automated rules (e.g., too many listings in short time)

**Tests:**

- Auto-flag logic tests
- Manual flag resolution

## Phase 8 — Performance, Reliability & Security

### 1. Caching & Rate Limiting

**Purpose:** Cache heavy list endpoints and rate limit write operations.

**Deliverables:**

- Redis caching for list endpoints
- Rate limiter middleware

**Tests:**

- Endpoint behavior with cache (cache warm/cold tests)
- Rate-limit enforcement tests

### 2. Background Tasks & Async Jobs

**Purpose:** Offload emails, image processing, notifications.

**Deliverables:**

- Background task queue (FastAPI BackgroundTasks or Celery) integration

**Tests:**

- Unit-test task invocation
- Mock worker execution

### 3. Logging, Monitoring & Metrics

**Purpose:** Observability for production.

**Deliverables:**

- Structured logs
- Metrics endpoints (Prometheus)
- Sentry for errors

**Tests:** Ensure errors are captured in error handler (unit tests for exception path).

### 4. Security Hardening

**Purpose:** Protect data and platform.

**Deliverables:**

- Secure headers
- Password hashing (bcrypt/argon2)
- JWT secrets rotation plan
- Input validation
- XSS/CSRF considerations for API clients
- CORS policy

**Tests:** Automated security tests for common cases (e.g., ensure endpoints sanitize inputs, enforce auth).

## Phase 9 — Testing Strategy (pytest) — Detailed

### 1. Testing Types & Scope

- **Unit tests:** Pure functions, services, validation
- **Integration tests:** DB + app using TestClient or AsyncClient
- **End-to-end tests:** Optional, with test front-end or API flows
- **Contract tests:** For webhooks/third-party interactions

### 2. Test Environment & Tooling

**Deliverables:**

- pytest, pytest-asyncio
- httpx/starlette.testclient
- factory_boy or model factories
- pytest-cov
- Fixtures for DB and client

**Acceptance:** Tests run in CI with a dedicated test DB (or SQLite in-memory if acceptable) and coverage threshold.

### 3. Fixtures & Factories

**Purpose:** Reusable test data.

**Deliverables:**

- Session-scoped DB setup/teardown fixture
- Per-test transaction rollback
- Factory functions for User, Property, images

**Tests:** Ensure isolation between tests (no cross-test contamination).

### 4. Mocking External Services

**Purpose:** Avoid hitting S3, Stripe, email providers in tests.

**Deliverables:**

- Mocks/stubs for object storage, payment gateway, email
- Use responses or pytest monkeypatch

**Tests:** Assertions that correct calls would have been made.

### 5. Integration Tests for Critical Flows

**Examples to include:**

- Register → Login → Create Property → Upload Images → List / Get property
- Favorite a property → Verify in user favorites
- Contact form → message created & notification triggered
- Payment webhook → subscription activated

**Acceptance:** Full flows pass in CI.

### 6. Testing Non-functional Behavior

- Tests for pagination limits, sorting correctness, search filters, geo queries
- Load tests: optional separate (locust/k6) — not pytest but part of QA

### 7. CI Integration

**Purpose:** Run tests on each push.

**Deliverables:**

- CI pipeline (GitHub Actions example) that:
  - Sets up DB
  - Runs migrations
  - Runs tests
  - Runs linters
  - Reports coverage

**Acceptance:** PRs must pass pipeline before merging.

## Phase 10 — Documentation, Developer Ergonomics & Release

### 1. API Docs & OpenAPI

**Deliverables:**

- Properly documented Pydantic schemas and routers so FastAPI autogenerates OpenAPI
- Extra examples for key endpoints

**Tests:** Simple check that OpenAPI contains expected endpoints.

### 2. README & Onboarding

**Deliverables:**

- How to run dev server
- Run tests
- Env vars
- Dev seed script

**Acceptance:** New developer can run app + tests following README.

### 3. Deployment Checklist

**Deliverables:**

- Containerization (Dockerfile)
- Helm or similar manifest
- Env config
- Secrets management
- Migration process
- Health checks

**Acceptance:** One-click deploy to staging.

### 4. Post-launch

- Feature flags for new features
- Analytics instrumentation
- Scheduled security scans
- Privacy/compliance documentation (GDPR if applicable)

---

## Acceptance Checklist

For each step, ensure the following acceptance criteria are met:

- ✅ Code compiles / server starts
- ✅ Migrations run without error
- ✅ Unit tests for the feature pass
- ✅ Integration tests for main flow pass
- ✅ Security checks for endpoints
- ✅ Documentation for the feature exists

## Testing Priorities

**What to write first:**

1. **Core auth & user tests** (register/login, token)
2. **DB model tests + migrations**
3. **Property CRUD integration tests**
4. **Image upload (mocked storage) tests**
5. **Search / filtering tests**
6. **Favorites and messages**
7. **Admin flows & payment/webhook tests last** (complex external integrations mocked)

## Extras / Nice-to-Have

- **Contract tests** for external APIs (Stripe, S3) so you don't break integrations
- **Canary test environment** and staging deployment
- **E2E smoke tests** after deployments

---

## Next Steps

If you want, pick any numbered step and I will:

- **Produce the exact data model and migration** for it, or
- **Produce the API endpoint spec** (schemas + request/response examples), or
- **Write the pytest tests** for that step

**Tell me which step you've noted** and I'll output the next artifact — e.g., "Create a model for Property" or "Write tests for auth" and I'll generate them.
