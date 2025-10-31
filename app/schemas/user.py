from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.ADMIN


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class Token(BaseModel):
    access_token: str
    token_type: str
