import json
import requests
import smtplib
import asyncio
import logging
from typing import Optional
from pywebpush import webpush, WebPushException
from email.message import EmailMessage
from app.config import settings
from app.database import SessionLocal
from app.models.notification import UserPushToken, Notification
from app.models.user import User

logger = logging.getLogger(__name__)


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
    inner = sub.get("subscription") if isinstance(sub.get("subscription"), dict) else None
    if inner and inner.get("endpoint"):
        return inner
    return sub


def send_web_push(subscription_info: dict, title: str, body: str, data: dict):
    sub = _normalize_subscription(subscription_info)
    if not sub or not sub.get("endpoint"):
        logger.warning("Web push skipped: subscription missing endpoint")
        return {"ok": False, "detail": "subscription missing endpoint"}
    vapid_claims = {**settings.VAPID_CLAIMS, "aud": settings.VAPID_AUDIENCE}
    try:
        webpush(
            sub,
            json.dumps({"title": title, "body": body, "data": data}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=vapid_claims,
        )
        return {"ok": True}
    except WebPushException as ex:
        logger.warning(
            "Web push failed: %s (endpoint: %s)",
            ex,
            sub.get("endpoint", "")[:80],
        )
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
            if token.expo_token:
                results["expo"] = send_expo_push(token.expo_token, title, body, payload)
            if token.web_push_subscription:
                try:
                    sub = json.loads(token.web_push_subscription)
                    results["web"] = send_web_push(sub, title, body, payload)
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
