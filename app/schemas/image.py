from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ImageBase(BaseModel):
    property_id: int


class ImageUpload(ImageBase):
    is_primary: bool
    order_index: int
    alt_text: str


class ImageResponse(BaseModel):
    id: int
    property_id: int
    created_at: datetime
    is_primary: bool
    order_index: int
    alt_text: str
    file_url: str

    model_config = ConfigDict(from_attributes=True)
