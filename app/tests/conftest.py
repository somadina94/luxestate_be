import os
import asyncio
import random as _random
import types
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

# CRITICAL: Set test database URL BEFORE importing any app modules
# This prevents app.database from creating a connection to production Supabase
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TESTING"] = "true"

from app.main import app
from app.database import Base
from app.routers import auth as auth_router
import app.Middleware.audit_middleware as audit_mw

# Import all models to ensure they're registered with Base.metadata
from app.models import (
    user,
    property,
    property_images,
    favorite,
    chat,
    notification,
    ticket,
    subscription,
    seller_subscription_plan,
    announcement,
    audit_log,
)
import app.database as db_module
import app.utils.email_utils as email_utils
from app.services import subscription as subscription_service_module
from app.models.subscription import SubscriptionStatus


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # share same in-memory DB across connections
    )
    # Don't create tables here - let db_session fixture handle it
    # This ensures tables are created fresh for each test with latest schema
    return engine


@pytest.fixture()
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    # Fresh schema per test to avoid cross-test data (e.g., unique email)
    # Drop all tables to ensure clean slate
    Base.metadata.drop_all(bind=test_engine)

    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def patch_sessionlocal(monkeypatch, test_engine, db_session):
    # CRITICAL: Patch engine FIRST before any SessionLocal patches
    # This ensures all sessions use the test engine where tables are created
    monkeypatch.setattr(db_module, "engine", test_engine, raising=False)

    # Patch the SessionLocal used by routers to our testing session factory
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Patch SessionLocal to a real session factory bound to the shared test engine
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal, raising=True)
    
    # Patch SessionLocal in dependencies.py (used by db_dependency)
    import app.dependencies as dependencies_module
    monkeypatch.setattr(dependencies_module, "SessionLocal", TestingSessionLocal, raising=True)
    # Also patch the get_db function in dependencies to use test SessionLocal
    def test_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    monkeypatch.setattr(dependencies_module, "get_db", test_get_db, raising=True)
    
    # Patch audit middleware SessionLocal similarly
    monkeypatch.setattr(audit_mw, "SessionLocal", TestingSessionLocal, raising=True)

    # Patch all routers that import SessionLocal directly
    # Most routers have their own get_db() that uses SessionLocal()
    router_modules = [
        "app.routers.stripe_checkout",
        "app.routers.favorites", 
        "app.routers.properties",
        "app.routers.auth",
        "app.routers.user",
        "app.routers.chat",
        "app.routers.websocket",
        "app.routers.admin",
        "app.routers.seller_subscription",
        "app.routers.ticket",
        "app.routers.push",
        "app.routers.announcements",
        "app.routers.notifications",
        "app.routers.images",
    ]
    
    for router_path in router_modules:
        try:
            router_module = __import__(router_path, fromlist=[""])
            if hasattr(router_module, "SessionLocal"):
                monkeypatch.setattr(router_module, "SessionLocal", TestingSessionLocal, raising=False)
            if hasattr(router_module, "get_db"):
                monkeypatch.setattr(router_module, "get_db", test_get_db, raising=False)
        except ImportError:
            pass  # Skip if module doesn't exist

    # Also patch main.py's get_db if it exists
    from app import main as main_module
    if hasattr(main_module, "get_db"):
        # Replace the get_db function to use our test SessionLocal
        def get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()
        monkeypatch.setattr(main_module, "get_db", get_db, raising=False)

    # Disable rate limiter globally for tests
    if hasattr(app.state, "limiter"):
        setattr(app.state.limiter, "enabled", False)
    yield


@pytest.fixture(autouse=True)
def patch_email_and_random(monkeypatch):
    # Make verification email async no-op
    async def _send_verification_email(email: str, code: str):
        return True

    # Patch in the email_utils module (where it's defined)
    monkeypatch.setattr(
        email_utils, "send_verification_email", _send_verification_email, raising=True
    )
    # ALSO patch in the auth router module (where it's imported and used)
    monkeypatch.setattr(
        auth_router, "send_verification_email", _send_verification_email, raising=True
    )

    # Mock send_email from notifications service (used by tickets)
    from app.services import notifications as notifications_module
    from app.services import tickets as tickets_module

    def _mock_send_email(to_email: str, subject: str, body: str):
        return True  # No-op for tests

    monkeypatch.setattr(
        notifications_module, "send_email", _mock_send_email, raising=True
    )
    # Also patch where it's imported in tickets service
    monkeypatch.setattr(tickets_module, "send_email", _mock_send_email, raising=True)

    # Fix the random code to deterministic value
    monkeypatch.setattr(_random, "randint", lambda a, b: 123456, raising=True)

    # Make subscription check always return active PAID for tests using it
    class _SubObj:
        def __init__(self):
            self.status = SubscriptionStatus.PAID

    def _get_user_active_subscription(self, user_id: int):
        return _SubObj()

    monkeypatch.setattr(
        subscription_service_module.SubscriptionService,
        "get_user_active_subscription",
        _get_user_active_subscription,
        raising=True,
    )
    yield


@pytest.fixture()
def client():
    return TestClient(app)
