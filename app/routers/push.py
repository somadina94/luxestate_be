from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pywebpush import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.auth_service import get_current_user
from app.models.notification import UserPushToken
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/push", tags=["Push"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_push_token(
    payload: dict,
    http_req: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    payload example:
    { "expo_token": "ExponentPushToken[...]",
      "web_push_subscription": { ... }  # optional
    }
    """
    expo_token = payload.get("expo_token")
    web_sub = payload.get("web_push_subscription")
    u = db.query(UserPushToken).filter(UserPushToken.user_id == user["id"]).first()
    if not u:
        u = UserPushToken(
            user_id=user["id"],
            expo_token=expo_token,
            web_push_subscription=json.dumps(web_sub) if web_sub else None,
        )
        db.add(u)
    else:
        if expo_token:
            u.expo_token = expo_token
        if web_sub:
            u.web_push_subscription = json.dumps(web_sub)
        u.updated_at = datetime.utcnow()
    db.commit()
    AuditLogService().create_log(
        db=db,
        action="push.register_token",
        resource_type="notification",
        resource_id=getattr(u, "id", None),
        user_id=user["id"],
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=http_req.headers.get("x-forwarded-for"),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"ok": True}
