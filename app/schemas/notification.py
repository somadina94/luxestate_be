from pydantic import BaseModel


class WebPushSubscribe(BaseModel):
    subscription: dict
