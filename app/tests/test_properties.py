from datetime import datetime, timedelta, timezone
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole
from app.models.seller_subscription_plan import (
    SubscriptionPlan,
    SubscriptionPlanDurationType,
)
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.property import PropertyType, ListingType


def _seed_seller_with_subscription(db):
    user = User(
        email="seller@example.com",
        password_hash="x",
        first_name="Sell",
        last_name="Er",
        role=UserRole.SELLER,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    plan = SubscriptionPlan(
        name="Basic",
        description="",
        price=10.0,
        currency="USD",
        duration=30,
        duration_type=SubscriptionPlanDurationType.MONTH,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    sub = Subscription(
        user_id=user.id,
        subscription_plan_id=plan.id,
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=30),
        status=SubscriptionStatus.PAID.value,
    )
    db.add(sub)
    db.commit()
    return user


def _auth_headers(db):
    user = _seed_seller_with_subscription(db)
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {token}"}


def _property_payload():
    return {
        "title": "Nice House",
        "description": "A lovely place",
        "price": 250000,
        "currency": "USD",
        "address": "123 Main",
        "city": "Town",
        "state": "ST",
        "zip_code": "00000",
        "country": "USA",
        "latitude": 10.0,
        "longitude": 11.0,
        "property_type": PropertyType.HOUSE.value,
        "bedrooms": 3,
        "bathrooms": 2,
        "square_feet": 1500,
        "lot_size": 0.2,
        "year_built": 2010,
        "features": ["garage"],
        "amenities": ["gym"],
        "listing_type": ListingType.SALE.value,
    }


def test_create_property(client, db_session):
    headers = _auth_headers(db_session)
    r = client.post("/properties/", json=_property_payload(), headers=headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Nice House"
    assert data["price"] == 250000


def test_search_properties(client, db_session):
    headers = _auth_headers(db_session)
    client.post("/properties/", json=_property_payload(), headers=headers)
    r = client.get("/properties/search", params={"city": "Town", "min_price": 100000})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1


def test_update_and_delete_property(client, db_session):
    headers = _auth_headers(db_session)
    res = client.post("/properties/", json=_property_payload(), headers=headers)
    pid = res.json()["id"]
    up = client.patch(f"/properties/{pid}", json={"price": 260000}, headers=headers)
    assert up.status_code == 200
    get = client.get(f"/properties/{pid}")
    assert get.status_code == 200 and get.json()["price"] == 260000
    delr = client.delete(f"/properties/{pid}", headers=headers)
    assert delr.status_code == 204
