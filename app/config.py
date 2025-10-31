from pydantic_settings import BaseSettings
from pydantic import ConfigDict


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

    SECRET_KEY: str
    ALGORITHM: str

    EMAIL_HOST: str
    EMAIL_PORT: str
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str

    EXPO_PUSH_URL: str
    VAPID_PUBLIC_KEY: str
    VAPID_PRIVATE_KEY: str
    VAPID_CLAIMS: dict[str, str]

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str
    STRIPE_SUCCESS_URL: str
    STRIPE_CANCEL_URL: str
    STRIPE_WEBHOOK_SECRET: str

    model_config = ConfigDict(env_file=".env")


settings = Settings()
