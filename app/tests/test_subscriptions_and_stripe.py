from datetime import datetime, timedelta
import types
import pytest
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole
from app.models.seller_subscription_plan import (
    SubscriptionPlan,
    SubscriptionPlanDurationType,
)
from app.models.subscription import Subscription, SubscriptionStatus


def _seed_user(db, role=UserRole.ADMIN, email="admin@example.com"):
    u = User(
        email=email,
        password_hash="x",
        first_name="A",
        last_name="D",
        role=role,
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _headers(db, user):
    token = create_access_token(user.email, user.id, user.role.value, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_subscriptions_endpoints(client, db_session):
    admin = _seed_user(db_session, role=UserRole.ADMIN)
    user = _seed_user(db_session, role=UserRole.SELLER, email="seller2@example.com")

    plan = SubscriptionPlan(
        name="Pro",
        description="",
        price=20.0,
        currency="USD",
        duration=30,
        duration_type=SubscriptionPlanDurationType.DAY,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    sub = Subscription(
        user_id=user.id,
        subscription_plan_id=plan.id,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        status=SubscriptionStatus.PAID,
    )
    db_session.add(sub)
    db_session.commit()

    # Admin list all
    r = client.get("/subscriptions/", headers=_headers(db_session, admin))
    assert r.status_code == 200

    # User list own
    r2 = client.get("/subscriptions/user/all", headers=_headers(db_session, user))
    assert r2.status_code == 200
    assert len(r2.json()) >= 1

    # User active
    r3 = client.get("/subscriptions/user/active", headers=_headers(db_session, user))
    assert r3.status_code == 200


def test_stripe_checkout_create_and_webhook(client, db_session, monkeypatch):
    # Seed user and plan
    user = _seed_user(db_session, role=UserRole.SELLER, email="buyer@example.com")
    plan = SubscriptionPlan(
        name="Basic",
        description="",
        price=10.0,
        currency="USD",
        duration=30,
        duration_type=SubscriptionPlanDurationType.DAY,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    # Mock stripe session creation
    import stripe as _stripe

    class _DummySession:
        def __init__(self, id="cs_test_123"):
            self.id = id
        
        def __getitem__(self, k):
            return getattr(self, k)

    def _fake_create(**kwargs):
        return _DummySession()

    monkeypatch.setattr(_stripe.checkout.Session, "create", _fake_create, raising=True)

    # Create checkout session
    headers = _headers(db_session, user)
    payload = {"subscription_plan_id": plan.id}
    r = client.post("/stripe_checkout/", headers=headers, json=payload)
    assert r.status_code == 200
    assert r.json()["id"]

    # Webhook: mock signature verify and settings secret
    from app.services import stripe_checkout as sc_mod

    class _Event(dict):
        pass

    def _fake_construct_event(payload, sig_header, secret):
        return _Event(
            type="checkout.session.completed",
            data={
                "object": {
                    "metadata": {"user_id": user.id, "subscription_plan_id": plan.id}
                }
            },
        )

    monkeypatch.setattr(sc_mod.stripe.Webhook, "construct_event", staticmethod(_fake_construct_event), raising=True)
    monkeypatch.setattr(sc_mod.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test", raising=True)

    wr = client.post("/stripe_checkout/webhook", data=b"{}", headers={"stripe-signature": "t"})
    assert wr.status_code == 200

