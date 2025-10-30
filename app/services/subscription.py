from fastapi import HTTPException
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.models.subscription import Subscription, SubscriptionStatus
from sqlalchemy.orm import Session


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def create_subscription(self, subscription_data: SubscriptionCreate):
        new_subscription = Subscription(**subscription_data.dict())
        self.db.add(new_subscription)
        self.db.commit()
        self.db.refresh(new_subscription)
        return new_subscription

    def get_subscription(self, subscription_id: int):
        return (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )

    def update_subscription(
        self, subscription_id: int, subscription_data: SubscriptionUpdate
    ):
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        subscription.update(subscription_data.dict())
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def get_subscriptions(self):
        return self.db.query(Subscription).all()

    def get_user_subscriptions(self, user_id: int):
        return self.db.query(Subscription).filter(Subscription.user_id == user_id).all()

    def get_subscription_by_id(self, subscription_id: int):
        return (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )

    def get_user_active_subscription(self, user_id: int):
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.PAID.value,
            )
            .order_by(Subscription.end_date.desc())
            .first()
        )

    def cancel_subscription(self, subscription_id: int):
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        subscription.status = SubscriptionStatus.CANCELLED
        self.db.commit()
        self.db.refresh(subscription)
        return subscription
