from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from app.database import SessionLocal
from app.dependencies import Permission, require_permission
from app.services.auth_service import get_current_user
from app.services.tickets import TicketService
from app.models.ticket import Ticket, TicketMessage
from app.schemas.ticket import (
    MessageCreate,
    MessageResponse,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
)

router = APIRouter(prefix="/ticket", tags=["ticket"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
admin_dependency = Annotated[
    dict, Depends(require_permission(Permission.MANAGE_TICKETS))
]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_ticket(db: db_dependency, user: user_dependency, request: TicketCreate):
    return TicketService(db).create_ticket(request, user.get("id"))


@router.get("/", response_model=List[TicketResponse], status_code=status.HTTP_200_OK)
def get_all_tickets(
    db: db_dependency,
    user: admin_dependency,
):
    return TicketService(db).get_tickets_with_messages()


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ticket(db: db_dependency, user: admin_dependency, ticket_id: int):
    return TicketService(db).delete_ticket(ticket_id)


@router.get(
    "/user",
    response_model=List[TicketResponse],
    status_code=status.HTTP_200_OK,
)
def get_user_tickets(db: db_dependency, user: user_dependency):
    return TicketService(db).get_user_tickets(user.get("id"))


@router.post(
    "/message/{ticket_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    db: db_dependency,
    user: user_dependency,
    message_request: MessageCreate,
    ticket_id: int,
):
    return TicketService(db).add_message(
        ticket_id, user.get("id"), message_request.message
    )


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
)
def post_message(
    db: db_dependency,
    user: admin_dependency,
    ticket_request: TicketUpdate,
    ticket_id: int,
):
    return TicketService(db).update_ticket(
        ticket_id,
        ticket_request,
    )
