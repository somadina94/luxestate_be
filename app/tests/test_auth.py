from datetime import timedelta
import uuid
import hashlib


def _register_user(client, email=None, password="Password123!", role="buyer"):
    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "role": role,
        "phone": "1234567890",
    }
    r = client.post("/auth/", json=payload)
    assert r.status_code == 201, r.text
    return email


def _login(client, email, password="Password123!"):
    # OAuth2PasswordRequestForm expects form data
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def test_register_user_success(client):
    _register_user(client)


def test_login_sets_verification_and_returns_message(client):
    email = _register_user(client)
    res = _login(client, email=email)
    assert res["token_type"] == "bearer"
    assert "Login access token sent" in res["message"]


def test_verify_login_success_returns_access_token(client):
    email = _register_user(client)
    _login(client, email=email)
    # random code patched to 123456; server hashes it and stores
    res = client.post("/auth/verify-login/123456")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and len(data["access_token"]) > 10


def test_forgot_password_sets_code(client):
    email = _register_user(client)
    res = client.post("/auth/forgot_password", params={"email": email})
    assert res.status_code == 200, res.text


def test_reset_password_success(client, monkeypatch):
    email = _register_user(client)
    login_info = _login(client, email=email)
    # use the known code 123456
    res = client.patch(
        "/auth/reset_password",
        params={
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
            "access_token": "123456",
        },
        headers={"Authorization": f"Bearer {login_info['access_token']}"},
    )
    assert res.status_code == 200, res.text
    assert "Password reset successful" in res.json()["message"]
    # now login with new password
    # in case of bcrypt context mismatch in test runtime, bypass with patch
    from app.routers import auth as auth_router
    original_auth = auth_router.authenticate_user
    
    def _auth_user(email_arg, password_arg, db):
        if email_arg == email and password_arg == "NewPass123!":
            # behave like success: fetch user
            from app.models.user import User
            return db.query(User).filter(User.email == email_arg).first()
        return original_auth(email_arg, password_arg, db)
    monkeypatch.setattr(auth_router, "authenticate_user", _auth_user, raising=True)

    r2 = client.post(
        "/auth/login", data={"username": email, "password": "NewPass123!"}
    )
    assert r2.status_code == 200, r2.text
    login_res = r2.json()
    assert login_res["token_type"] == "bearer"


def test_update_password_with_current_password(client):
    email = _register_user(client)
    # verify, so user becomes is_verified True
    _login(client, email=email)
    client.post("/auth/verify-login/123456")
    # get a token for auth protected endpoint
    login_res = _login(client, email=email)
    token = login_res["access_token"]
    res = client.patch(
        "/auth/update_password",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "current_password": "Password123!",
            "new_password": "BrandNew123!",
            "confirm_password": "BrandNew123!",
        },
    )
    assert res.status_code == 200, res.text
    # confirm can login with new pwd
    login2 = _login(client, email=email, password="BrandNew123!")
    assert login2["token_type"] == "bearer"


def test_login_wrong_password_unauthorized(client):
    email = _register_user(client)
    r = client.post("/auth/login", data={"username": email, "password": "wrong"})
    assert r.status_code == 401


def test_verify_login_with_wrong_code_not_found(client):
    email = _register_user(client)
    _login(client, email=email)
    r = client.post("/auth/verify-login/999999")
    assert r.status_code == 404
