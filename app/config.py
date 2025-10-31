from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
import json


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./luxestate.db"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    EMAIL_HOST: str
    EMAIL_PORT: str
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str

    EXPO_PUSH_URL: str
    VAPID_PUBLIC_KEY: str
    VAPID_PRIVATE_KEY: str
    VAPID_CLAIMS: dict[str, str]

    @field_validator("VAPID_CLAIMS", mode="before")
    @classmethod
    def parse_vapid_claims(cls, v):
        """Parse VAPID_CLAIMS from JSON string if it's a string, otherwise return as-is."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If JSON parsing fails, return the string wrapped in a dict or raise
                raise ValueError(f"Invalid JSON in VAPID_CLAIMS: {v}")
        return v

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str
    STRIPE_SUCCESS_URL: str
    STRIPE_CANCEL_URL: str
    STRIPE_WEBHOOK_SECRET: str

    model_config = ConfigDict(env_file=".env")


settings = Settings()
