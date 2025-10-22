from email.message import EmailMessage
from aiosmtplib import send
from app.config import settings


async def send_verification_email(to_email: str, code: str):
    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = "Your Verification Code"
    message.set_content(f"Your verification code is: {code}")

    await send(
        message,
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_USERNAME,
        password=settings.EMAIL_PASSWORD,
        start_tls=True,
    )
