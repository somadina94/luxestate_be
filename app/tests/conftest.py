import os
import asyncio
import random as _random
import types
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base
from app.routers import auth as auth_router
import app.Middleware.audit_middleware as audit_mw
from app.models import user as _user_model  # ensure tables are registered
from app.models import audit_log as _audit_model
import app.database as db_module
import app.utils.email_utils as email_utils
from app.services import subscription as subscription_service_module
from app.models.subscription import SubscriptionStatus

# Set TESTING environment variable to prevent email sending
os.environ["TESTING"] = "true"


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
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    # Fresh schema per test to avoid cross-test data (e.g., unique email)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def patch_sessionlocal(monkeypatch, test_engine, db_session):
    # Patch the SessionLocal used by routers to our testing session factory
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Patch SessionLocal to a real session factory bound to the shared test engine
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal, raising=True)
    # Patch audit middleware SessionLocal similarly
    monkeypatch.setattr(audit_mw, "SessionLocal", TestingSessionLocal, raising=True)
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
