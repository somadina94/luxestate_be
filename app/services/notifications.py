import json
import time
from urllib.parse import urlparse
import requests
import smtplib
from pywebpush import webpush, WebPushException
from email.message import EmailMessage
from app.config import settings
from app.database import SessionLocal
from app.models.notification import UserPushToken, Notification
from app.models.user import User


# ---------- Expo push ----------
def send_expo_push(expo_token: str, title: str, body: str, data: dict):
    if not expo_token or not expo_token.startswith("ExponentPushToken"):
        return {"status": "invalid_token"}
    payload = {
        "to": expo_token,
        "title": title,
        "body": body,
        "data": data,
        "priority": "high",
    }
    res = requests.post(settings.EXPO_PUSH_URL, json=payload, timeout=10)
    try:
        return res.json()
    except Exception:
        return {"status": res.status_code}


# ---------- Web Push ----------
def _normalize_subscription(sub: dict) -> dict:
    """Return subscription dict with 'endpoint' and 'keys' at top level. Handles double-nested { subscription: {...} } from frontend."""
    if not sub:
        return sub
    if "endpoint" in sub and sub.get("endpoint"):
        return sub
    inner = (
        sub.get("subscription") if isinstance(sub.get("subscription"), dict) else None
    )
    if inner and inner.get("endpoint"):
        return inner
    return sub


def send_web_push(subscription_info: dict, title: str, body: str, data: dict):
    sub = _normalize_subscription(subscription_info)
    if not sub or not sub.get("endpoint"):
        return {"ok": False, "detail": "subscription missing endpoint"}
    endpoint = sub.get("endpoint", "")
    # aud MUST be the origin of the push resource URL (the endpoint), not the frontend origin.
    parsed = urlparse(endpoint)
    aud = (
        f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme and parsed.netloc
        else settings.VAPID_AUDIENCE
    )
    vapid_claims = {
        **settings.VAPID_CLAIMS,
        "aud": aud,
        "exp": int(time.time()) + 12 * 3600,
    }

    try:
        webpush(
            sub,
            json.dumps({"title": title, "body": body, "data": data}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=vapid_claims,
            ttl=86400,  # Required by WNS/Edge (400 without it); 24h in seconds
        )
        return {"ok": True}
    except WebPushException as ex:
        return {"ok": False, "detail": str(ex)}


# ---------- Email via Zoho ----------
def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.starttls()
        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        server.send_message(msg)
    return {"sent": True}


# ---------- Combined notification dispatcher ----------
def dispatch_notification(user_id: int, title: str, body: str, payload: dict):
    """
    Sync function that:
    - Persists Notification row
    - Attempts real-time websocket send is done elsewhere (manager)
    - Sends Expo / WebPush / Email as fallback
    """
    db = SessionLocal()
    try:
        n = Notification(
            user_id=user_id, title=title, body=body, payload=json.dumps(payload)
        )
        db.add(n)
        db.commit()

        token = db.query(UserPushToken).filter(UserPushToken.user_id == user_id).first()
        results = {"expo": None, "web": None, "email": None}
        if token:
            user = db.query(User).filter(User.id == user_id).first()
            push_data = dict(payload)
            if user and user.role:
                push_data["path"] = (
                    f"/buyer-dashboard/notifications/{n.id}"
                    if user.role == "buyer"
                    else (
                        f"/seller-dashboard/notifications/{n.id}"
                        if user.role == "seller"
                        else (
                            f"/admin-dashboard/notifications/{n.id}"
                            if user.role == "admin"
                            else f"/buyer-dashboard/notifications/{n.id}"
                        )
                    )
                )
            else:
                push_data["path"] = f"/buyer-dashboard/notifications/{n.id}"
            if token.expo_token:
                results["expo"] = send_expo_push(token.expo_token, title, body, payload)
            if token.web_push_subscription:
                try:
                    sub = json.loads(token.web_push_subscription)
                    results["web"] = send_web_push(sub, title, body, push_data)
                except Exception as e:
                    results["web"] = {"ok": False, "detail": str(e)}

        user = db.query(User).filter(User.id == user_id).first()
        if (not results["expo"] or results["expo"] == "invalid_token") and not results[
            "web"
        ]:
            if user and user.email:
                results["email"] = send_email(user.email, title, body)

        return results
    finally:
        db.close()
