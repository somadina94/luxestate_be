from typing import List

from pydantic import BaseModel


class WebPushSubscribe(BaseModel):
    subscription: dict


class MarkReadBody(BaseModel):
    """PATCH /notifications/read body: object with optional additional properties (e.g. ids)."""

    ids: List[int] = []
    model_config = {"extra": "allow"}  # allow additional properties per API schema
