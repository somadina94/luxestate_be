from datetime import datetime, timedelta
import json
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole
from app.models.notification import Notification


def _seed_user(db):
    user = User(
        email="note@example.com",
        password_hash="x",
        first_name="N",
        last_name="O",
        role=UserRole.BUYER,
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user):
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {token}"}


def test_notifications_list_and_mark_read(client, db_session):
    user = _seed_user(db_session)
    # seed a notification
    n = Notification(user_id=user.id, title="t", body="b", payload=json.dumps({}))
    db_session.add(n)
    db_session.commit()
    n_id = n.id
    headers = _auth_headers(user)
    list_r = client.get("/notifications/", headers=headers)
    assert list_r.status_code == 200
    ids = {"ids": [n_id]}
    mark = client.patch("/notifications/read", headers=headers, json=ids)
    assert mark.status_code == 200


def test_webpush_subscribe(client, db_session):
    user = _seed_user(db_session)
    headers = _auth_headers(user)
    payload = {
        "subscription": {
            "endpoint": "https://example",
            "keys": {"p256dh": "x", "auth": "y"},
        }
    }
    r = client.post("/notifications/webpush/subscribe", headers=headers, json=payload)
    assert r.status_code == 201

