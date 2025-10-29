from fastapi import APIRouter, Response, status, Request
from typing import Annotated
from fastapi import Depends
from app.schemas.stripe_checkout import StripeCheckoutCreate, StripeCheckoutResponse
from app.services.auth_service import get_current_user
from app.database import SessionLocal
from sqlalchemy.orm import Session

from app.services.stripe_checkout import StripeCheckoutService

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
    return StripeCheckoutService(db).create_checkout_session(user, request)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(request: Request, db: db_dependency):
    await StripeCheckoutService(db).handle_webhook(request=request)
    return Response(status_code=status.HTTP_200_OK)
