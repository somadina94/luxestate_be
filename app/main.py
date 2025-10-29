from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from starlette import status
from app.database import Base, SessionLocal, engine


from app.routers import (
    auth,
    admin,
    user,
    properties,
    favorites,
    images,
    websocket,
    chat,
    notifications,
    push,
    ticket,
    seller_subscription,
    stripe_checkout,
    subscription,
)

app = FastAPI()
Base.metadata.create_all(bind=engine)


@app.get("/healthy", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "Healthy"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(properties.router)
app.include_router(favorites.router)
app.include_router(images.router)
app.include_router(websocket.router)
app.include_router(chat.router)
app.include_router(push.router)
app.include_router(notifications.router)
app.include_router(ticket.router)
app.include_router(seller_subscription.router)
app.include_router(stripe_checkout.router)
app.include_router(subscription.router)
