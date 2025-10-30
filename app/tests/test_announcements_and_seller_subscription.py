from datetime import datetime, timedelta
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole
from app.models.seller_subscription_plan import (
    SubscriptionPlan,
    SubscriptionPlanDurationType,
)


def _seed_admin(db):
    u = User(
        email="admin2@example.com",
        password_hash="x",
        first_name="Ad",
        last_name="Min",
        role=UserRole.ADMIN,
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


def test_announcements_crud(client, db_session):
    admin = _seed_admin(db_session)
    headers = _headers(db_session, admin)

    payload = {
        "title": "Maintenance",
        "content": "We will be down.",
        "link": None,
        "expires_at": datetime.utcnow().isoformat(),
    }
    c = client.post("/announcements/", headers=headers, json=payload)
    assert c.status_code == 201
    ann_id = c.json()["id"]

    lst = client.get("/announcements/")
    assert lst.status_code == 200

    up = client.put(
        f"/announcements/{ann_id}", headers=headers, json={"title": "Updated"}
    )
    assert up.status_code == 200
    assert up.json()["title"] == "Updated"

    de = client.delete(f"/announcements/{ann_id}", headers=headers)
    assert de.status_code == 200


def test_seller_subscription_plan_crud(client, db_session):
    admin = _seed_admin(db_session)
    headers = _headers(db_session, admin)

    payload = {
        "name": "Gold",
        "description": "",
        "price": 50.0,
        "currency": "USD",
        "duration": 30,
        "duration_type": SubscriptionPlanDurationType.DAY.value,
    }
    c = client.post("/seller_subscription/", headers=headers, json=payload)
    assert c.status_code == 201
    pid = c.json()["id"]

    ga = client.get("/seller_subscription/", headers=headers)
    assert ga.status_code == 200
    assert len(ga.json()) >= 1

    g1 = client.get(f"/seller_subscription/{pid}", headers=headers)
    assert g1.status_code == 200

    up = client.patch(f"/seller_subscription/{pid}", headers=headers, json={"price": 60.0})
    assert up.status_code == 200 and up.json()["price"] == 60.0

    de = client.delete(f"/seller_subscription/{pid}", headers=headers)
    assert de.status_code == 200


