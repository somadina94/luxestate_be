from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Database
    # Use absolute path for SQLite (default to /home/ubuntu/luxestate/luxestate.db)
    # Can be overridden with DATABASE_URL in .env
    DATABASE_URL: str = "sqlite:////home/ubuntu/luxestate/luxestate.db"

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
    VAPID_CLAIMS: dict[str, str] = {"sub": "mailto:support@jahbyte.com"}

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str
    STRIPE_SUCCESS_URL: str
    STRIPE_CANCEL_URL: str
    STRIPE_WEBHOOK_SECRET: str

    model_config = ConfigDict(env_file=".env")


settings = Settings()
