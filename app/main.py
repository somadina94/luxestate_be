from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from starlette import status
from app.database import Base, SessionLocal, engine
from app.routers import auth, admin, user

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
