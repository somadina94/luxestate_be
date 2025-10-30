import json
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from starlette import status
from app.schemas.notification import WebPushSubscribe
from app.services.auth_service import get_current_user
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models.notification import Notification, UserPushToken
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/")
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user), http_req: Request = None):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user["id"])
        .order_by(Notification.created_at.desc())
        .all()
    )
    AuditLogService().create_log(
        db=db,
        action="notification.list",
        resource_type="notification",
        resource_id=None,
        user_id=user["id"],
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for") if http_req else None,
        user_agent=http_req.headers.get("user-agent") if http_req else None,
        request_method=http_req.method if http_req else None,
        request_path=http_req.url.path if http_req else None,
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "body": r.body,
            "is_read": r.is_read,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.patch("/read")
def mark_read(ids: dict, db: Session = Depends(get_db), user=Depends(get_current_user), http_req: Request = None):
    ids_list = ids.get("ids", [])
    if not ids_list:
        return {"ok": False}
    db.query(Notification).filter(
        Notification.user_id == user["id"], Notification.id.in_(ids_list)
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    AuditLogService().create_log(
        db=db,
        action="notification.read",
        resource_type="notification",
        resource_id=None,
        user_id=user["id"],
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=http_req.headers.get("x-forwarded-for") if http_req else None,
        user_agent=http_req.headers.get("user-agent") if http_req else None,
        request_method=http_req.method if http_req else None,
        request_path=http_req.url.path if http_req else None,
    )
    return {"ok": True}


@router.post("/webpush/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe_web_push(
    request: WebPushSubscribe, db: db_dependency, user: user_dependency, http_req: Request
):
    subscription_data = json.dumps(request.subscription)

    token_entry = (
        db.query(UserPushToken).filter(UserPushToken.user_id == user["id"]).first()
    )

    if token_entry:
        # update existing record
        token_entry.web_push_subscription = subscription_data
    else:
        # create new token
        token_entry = UserPushToken(
            user_id=user["id"], web_push_subscription=subscription_data
        )
        db.add(token_entry)

    db.commit()
    AuditLogService().create_log(
        db=db,
        action="notification.webpush_subscribe",
        resource_type="notification",
        resource_id=getattr(token_entry, "id", None),
        user_id=user["id"],
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=http_req.headers.get("x-forwarded-for"),
        user_agent=http_req.headers.get("user-agent"),
        request_method=http_req.method,
        request_path=http_req.url.path,
    )
    return {"message": "Web push subscription saved"}
