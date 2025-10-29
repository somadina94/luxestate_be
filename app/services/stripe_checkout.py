from fastapi import HTTPException, Request
from app.config import settings
from app.models.user import User
from app.schemas.stripe_checkout import StripeCheckoutCreate
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models.seller_subscription_plan import SubscriptionPlan
import stripe
from app.models.subscription import Subscription, SubscriptionStatus
from datetime import datetime, timedelta

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeCheckoutService:
    def __init__(self, db: Session):
        self.db = db

    def create_checkout_session(self, user: User, request: StripeCheckoutCreate):
        subscription_plan = (
            self.db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.id == request.subscription_plan_id)
            .first()
        )
        if not subscription_plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(
                            subscription_plan.price * 100
                        ),  # amount in cents ($10.00)
                        "product_data": {
                            "name": subscription_plan.name,
                            "description": subscription_plan.description,
                        },
                    },
                    "quantity": 1,
                },
            ],
            metadata={
                "user_id": user.get("id"),
                "subscription_plan_id": subscription_plan.id,
            },
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
        )

        return session

    async def handle_webhook(self, request: Request):
        payload = await request.body()  # ✅ MUST use await
        sig_header = request.headers.get("stripe-signature")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        if not endpoint_secret:
            raise HTTPException(status_code=500, detail="Stripe webhook secret missing")

        # ✅ Validate webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=endpoint_secret,
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # ✅ Handle events
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            if "user_id" not in session["metadata"]:
                raise HTTPException(status_code=400, detail="Missing metadata: user_id")

            user = (
                self.db.query(User)
                .filter(User.id == session["metadata"]["user_id"])
                .first()
            )
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            subscription_plan = (
                self.db.query(SubscriptionPlan)
                .filter(
                    SubscriptionPlan.id
                    == session["metadata"].get("subscription_plan_id")
                )
                .first()
            )
            if not subscription_plan:
                raise HTTPException(
                    status_code=404, detail="Subscription plan not found"
                )

            subscription = Subscription(
                user_id=user.id,
                subscription_plan_id=session["metadata"].get("subscription_plan_id"),
                status=SubscriptionStatus.PAID,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=subscription_plan.duration),
            )
            self.db.add(subscription)
            self.db.commit()
            return {"status": "success"}

        elif event["type"] == "checkout.session.expired":
            session = event["data"]["object"]
            return self._update_subscription_status(session, SubscriptionStatus.EXPIRED)

        elif event["type"] == "checkout.session.canceled":
            session = event["data"]["object"]
            return self._update_subscription_status(
                session, SubscriptionStatus.CANCELLED
            )

        return {"status": "ignored"}
