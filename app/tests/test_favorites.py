from datetime import datetime, timedelta, timezone
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole
from app.models.property import Property, PropertyType, ListingType


def _seed_user_and_property(db):
    user = User(
        email="favuser@example.com",
        password_hash="x",
        first_name="F",
        last_name="U",
        role=UserRole.BUYER,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    prop = Property(
        title="Prop",
        price=100.0,
        currency="USD",
        address="a",
        city="c",
        state="s",
        zip_code="z",
        country="USA",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        agent_id=user.id,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return user, prop


def _auth_headers(user):
    token = create_access_token(
        user.email, user.id, user.role.value, timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {token}"}


def test_favorites_add_list_remove(client, db_session):
    user, prop = _seed_user_and_property(db_session)
    prop_id = prop.id
    headers = _auth_headers(user)
    add = client.post(f"/favorites/{prop_id}", headers=headers)
    assert add.status_code == 201
    list_r = client.get("/favorites/me", headers=headers)
    assert list_r.status_code == 200
    assert any(row["property_id"] == prop_id for row in list_r.json())
    del_r = client.delete(f"/favorites/{prop_id}", headers=headers)
    assert del_r.status_code == 204
