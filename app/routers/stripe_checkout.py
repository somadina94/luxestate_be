from fastapi import APIRouter, Response, status, Request
from typing import Annotated
from fastapi import Depends
from app.schemas.stripe_checkout import StripeCheckoutCreate, StripeCheckoutResponse
from app.services.auth_service import get_current_user
from app.database import SessionLocal
from sqlalchemy.orm import Session

from app.services.stripe_checkout import StripeCheckoutService
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/stripe_checkout", tags=["stripe_checkout"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_description="Stripe checkout session created successfully",
)
def create_checkout_session(
    db: db_dependency, user: user_dependency, request: StripeCheckoutCreate
):
    result = StripeCheckoutService(db).create_checkout_session(user, request)
    # Log checkout initiation (do not log sensitive payment data)
    AuditLogService().create_log(
        db=db,
        action="subscription.checkout_initiated",
        resource_type="subscription",
        resource_id=None,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
    )
    return result


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(request: Request, db: db_dependency):
    await StripeCheckoutService(db).handle_webhook(request=request)
    # Best-effort log of webhook receipt; avoid reading stream twice
    AuditLogService().create_log(
        db=db,
        action="subscription.webhook_received",
        resource_type="subscription",
        resource_id=None,
        user_id=None,
        status="success",
        status_code=status.HTTP_200_OK,
        request_method="POST",
        request_path="/stripe_checkout/webhook",
    )
    return Response(status_code=status.HTTP_200_OK)
