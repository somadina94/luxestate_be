from datetime import datetime, timedelta, timezone
import pytest
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole


def _seed_user(db, role=UserRole.SELLER, email="u@example.com"):
    u = User(
        email=email,
        password_hash="x",
        first_name="T",
        last_name="U",
        role=role,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _auth_headers_for(db, user: User):
    token = create_access_token(user.email, user.id, user.role.value, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_require_permission_returns_401_on_missing_role(client, db_session, monkeypatch):
    # Monkeypatch get_current_user to simulate missing role
    from app import dependencies as deps
    from app.dependencies import Permission

    def _fake_current_user():
        return {"id": 1, "email": "x@example.com", "role": None}

    # Create minimal announcement payload
    payload = {
        "title": "Hello",
        "content": "World",
        "link": None,
        "expires_at": datetime.now(timezone.utc).isoformat(),
    }

    # Inject dependency wrapper that uses our fake current user
    monkeypatch.setattr("app.services.auth_service.get_current_user", _fake_current_user, raising=False)

    r = client.post("/announcements/", json=payload)
    assert r.status_code == 401


def test_user_profile_and_deactivate(client, db_session):
    u = _seed_user(db_session, role=UserRole.SELLER, email="seller_user@example.com")
    headers = _auth_headers_for(db_session, u)

    r = client.get("/users/", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == u.email

    d = client.delete("/users/deactivate", headers=headers)
    assert d.status_code == 200


def test_push_register_token(client, db_session):
    u = _seed_user(db_session, role=UserRole.BUYER, email="pushuser@example.com")
    headers = _auth_headers_for(db_session, u)
    payload = {"expo_token": "ExponentPushToken[test]", "web_push_subscription": {"endpoint": "https://example"}}
    r = client.post("/push/register", headers=headers, json=payload)
    assert r.status_code == 201
    assert r.json()["ok"] is True


