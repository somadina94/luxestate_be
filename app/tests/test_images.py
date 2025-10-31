from datetime import datetime, timedelta, timezone
from io import BytesIO
from fastapi import UploadFile
from app.services.auth_service import create_access_token
from app.models.user import User, UserRole
from app.models.property import Property, PropertyType
from app.models.property_images import PropertyImage
from app.services import image_service as image_service_module


def _seed_seller_and_property(db):
    user = User(
        email="img@example.com",
        password_hash="x",
        first_name="I",
        last_name="M",
        role=UserRole.SELLER,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    prop = Property(
        title="P",
        price=100.0,
        currency="USD",
        address="a",
        city="c",
        state="s",
        zip_code="z",
        country="USA",
        property_type=PropertyType.HOUSE,
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


def test_upload_and_delete_image(client, db_session, monkeypatch):
    user, prop = _seed_seller_and_property(db_session)
    headers = _auth_headers(user)

    # mock image service
    async def _upload_image(file, property_id):
        return {"public_id": "pid", "secure_url": "https://url"}

    async def _delete_image(key):
        return True

    monkeypatch.setattr(
        image_service_module.ImageService, "upload_image", staticmethod(_upload_image)
    )
    monkeypatch.setattr(
        image_service_module.ImageService, "delete_image", staticmethod(_delete_image)
    )
    # upload
    files = {"file": ("test.jpg", BytesIO(b"x"), "image/jpeg")}
    data = {"alt_text": "alt", "is_primary": "true", "order_index": "0"}
    r = client.post(
        f"/property_images/{prop.id}", headers=headers, files=files, data=data
    )
    assert r.status_code == 201, r.text
    # verify via API and then delete
    list_r = client.get(f"/property_images/{prop.id}", headers=headers)
    assert list_r.status_code == 200
    imgs = list_r.json()
    assert len(imgs) >= 1
    img_id = imgs[0]["id"]
    # delete
    delr = client.delete(f"/property_images/{img_id}", headers=headers)
    assert delr.status_code == 204
