import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status
from app.schemas.notification import MarkReadBody, WebPushSubscribe
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
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user), request: Request = None):
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
        ip_address=request.headers.get("x-forwarded-for") if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_method=request.method if request else None,
        request_path=request.url.path if request else None,
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


@router.get("/{notification_id}")
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    request: Request = None,
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user["id"])
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    AuditLogService().create_log(
        db=db,
        action="notification.get",
        resource_type="notification",
        resource_id=notification_id,
        user_id=user["id"],
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for") if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_method=request.method if request else None,
        request_path=request.url.path if request else None,
    )
    return {
        "id": notification.id,
        "title": notification.title,
        "body": notification.body,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    request: Request = None,
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user["id"])
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    db.delete(notification)
    db.commit()
    AuditLogService().create_log(
        db=db,
        action="notification.delete",
        resource_type="notification",
        resource_id=notification_id,
        user_id=user["id"],
        status="success",
        status_code=status.HTTP_204_NO_CONTENT,
        ip_address=request.headers.get("x-forwarded-for") if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_method=request.method if request else None,
        request_path=request.url.path if request else None,
    )


@router.patch("/read")
def mark_read(
    body: MarkReadBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    request: Request = None,
):
    ids_list = body.ids
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
        ip_address=request.headers.get("x-forwarded-for") if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_method=request.method if request else None,
        request_path=request.url.path if request else None,
    )
    return {"ok": True}


@router.post("/webpush/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe_web_push(
    request: WebPushSubscribe, db: db_dependency, user: user_dependency, request_http: Request
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
        ip_address=request_http.headers.get("x-forwarded-for"),
        user_agent=request_http.headers.get("user-agent"),
        request_method=request_http.method,
        request_path=request_http.url.path,
    )
    return {"message": "Web push subscription saved"}
