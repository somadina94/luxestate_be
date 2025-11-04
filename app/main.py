from typing import Annotated
from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    TimeoutError as SQLTimeoutError,
)
from starlette import status
from app.database import Base, SessionLocal, engine
from app.config import settings
from app.Middleware.audit_middleware import audit_log_middleware
from app import models
from app.limits import limiter, RateLimitExceeded, SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded as _RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import logging

logger = logging.getLogger(__name__)


from app.routers import (
    auth,
    admin,
    user,
    properties,
    favorites,
    images,
    websocket,
    chat,
    notifications,
    push,
    ticket,
    seller_subscription,
    stripe_checkout,
    subscription,
    announcements,
)

app = FastAPI()
# Base.metadata.create_all(bind=engine)
app.middleware("http")(audit_log_middleware)

# CORS (permissive for development; tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware and handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Database error handler
@app.exception_handler(OperationalError)
async def database_operational_error_handler(request: Request, exc: OperationalError):
    """Handle database connection/operation errors"""
    logger.error(f"Database operational error: {exc}", exc_info=True)
    error_msg = str(exc)

    # Check for common connection issues
    if "could not connect" in error_msg.lower() or "connection" in error_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Database connection error. Please try again.",
                "error": "database_connection_error",
                "hint": "If using Supabase, ensure you're using the connection pooling URL (port 6543) instead of direct connection (port 5432)",
            },
        )
    elif "timeout" in error_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "detail": "Database query timeout. Please try again.",
                "error": "database_timeout",
            },
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred", "error": "database_error"},
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy errors"""
    logger.error(f"Database error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred", "error": "database_error"},
    )


# Note: In production, disable this and use Alembic migrations instead
# Only create tables if using SQLite (for local dev), not for PostgreSQL/Supabase
if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)


@app.get("/healthy", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "Healthy"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(properties.router)
app.include_router(favorites.router)
app.include_router(images.router)
app.include_router(websocket.router)
app.include_router(chat.router)
app.include_router(push.router)
app.include_router(notifications.router)
app.include_router(ticket.router)
app.include_router(seller_subscription.router)
app.include_router(stripe_checkout.router)
app.include_router(subscription.router)
app.include_router(announcements.router)
