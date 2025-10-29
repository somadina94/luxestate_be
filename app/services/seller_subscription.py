from fastapi import HTTPException
from app.schemas.seller_subscription import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
)
from app.models.seller_subscription_plan import SubscriptionPlan
from sqlalchemy.orm import Session


class SellerSubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def create_subscription_plan(self, subscription_plan_data: SubscriptionPlanCreate):
        new_subscription_plan = SubscriptionPlan(**subscription_plan_data.dict())
        self.db.add(new_subscription_plan)
        self.db.commit()
        self.db.refresh(new_subscription_plan)
        return new_subscription_plan

    def get_subscription_plans(self):
        return self.db.query(SubscriptionPlan).all()

    def get_subscription_plan(self, subscription_plan_id: int):
        return (
            self.db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.id == subscription_plan_id)
            .first()
        )

    def update_subscription_plan(
        self, subscription_plan_id: int, subscription_plan_data: SubscriptionPlanUpdate
    ):
        subscription_plan = (
            self.db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.id == subscription_plan_id)
            .first()
        )
        if not subscription_plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        if subscription_plan_data.name is not None:
            subscription_plan.name = subscription_plan_data.name
        if subscription_plan_data.description is not None:
            subscription_plan.description = subscription_plan_data.description
        if subscription_plan_data.price is not None:
            subscription_plan.price = subscription_plan_data.price
        if subscription_plan_data.currency is not None:
            subscription_plan.currency = subscription_plan_data.currency
        if subscription_plan_data.duration is not None:
            subscription_plan.duration = subscription_plan_data.duration
        if subscription_plan_data.duration_type is not None:
            subscription_plan.duration_type = subscription_plan_data.duration_type
        self.db.commit()
        self.db.refresh(subscription_plan)
        return subscription_plan

    def delete_subscription_plan(self, subscription_plan_id: int):
        subscription_plan = (
            self.db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.id == subscription_plan_id)
            .first()
        )
        if not subscription_plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        self.db.delete(subscription_plan)
        self.db.commit()
        return {"detail": "Subscription plan deleted successfully"}
