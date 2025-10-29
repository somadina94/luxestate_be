import json
from typing import Annotated
from fastapi import APIRouter, Depends
from starlette import status
from app.schemas.notification import WebPushSubscribe
from app.services.auth_service import get_current_user
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models.notification import Notification, UserPushToken

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
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user["id"])
        .order_by(Notification.created_at.desc())
        .all()
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
def mark_read(ids: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ids_list = ids.get("ids", [])
    if not ids_list:
        return {"ok": False}
    db.query(Notification).filter(
        Notification.user_id == user["id"], Notification.id.in_(ids_list)
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"ok": True}


@router.post("/webpush/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe_web_push(
    request: WebPushSubscribe, db: db_dependency, user: user_dependency
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
    return {"message": "Web push subscription saved"}
