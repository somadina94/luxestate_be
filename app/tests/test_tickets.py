from datetime import datetime, timedelta, timezone
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole


def _seed_admin(db):
    user = User(
        email="admin@example.com",
        password_hash="x",
        first_name="A",
        last_name="D",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_user(db):
    user = User(
        email="u2@example.com",
        password_hash="x",
        first_name="U",
        last_name="2",
        role=UserRole.BUYER,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
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


def test_ticket_crud_and_message(client, db_session):
    user = _seed_user(db_session)
    headers_user = _auth_headers(user)
    # create
    payload = {"title": "Help", "description": "Issue text"}
    crt = client.post("/ticket/", headers=headers_user, json=payload)
    assert crt.status_code == 201
    # fetch user tickets to get id robustly
    my = client.get("/ticket/user", headers=headers_user)
    assert my.status_code == 200 and len(my.json()) >= 1
    tid = my.json()[0]["id"]
    # add message
    msg = client.post(
        f"/ticket/message/{tid}", headers=headers_user, json={"message": "hi"}
    )
    assert msg.status_code == 201
    # admin lists and deletes
    admin = _seed_admin(db_session)
    headers_admin = _auth_headers(admin)
    list_all = client.get("/ticket/", headers=headers_admin)
    assert list_all.status_code == 200
    delr = client.delete(f"/ticket/{tid}", headers=headers_admin)
    assert delr.status_code == 204

