# Import all models so they're registered with Base.metadata
from app.models.user import User
from app.models.property import Property
from app.models.property_images import PropertyImage
from app.models.favorite import Favorite
from app.models.chat import Conversation, Message
from app.models.notification import Notification, UserPushToken
from app.models.ticket import Ticket, TicketMessage
from app.models.subscription import Subscription
from app.models.seller_subscription_plan import SubscriptionPlan
from app.models.announcement import Announcement
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Property",
    "PropertyImage",
    "Favorite",
    "Conversation",
    "Message",
    "Notification",
    "UserPushToken",
    "Ticket",
    "TicketMessage",
    "Subscription",
    "SubscriptionPlan",
    "Announcement",
    "AuditLog",
]
