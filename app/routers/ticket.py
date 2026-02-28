from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Request
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
from app.services.audit_log_service import AuditLogService

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
def create_ticket(
    db: db_dependency,
    user: user_dependency,
    request: TicketCreate,
    request_http: Request,
):
    result = TicketService(db).create_ticket(request, user.get("id"))
    AuditLogService().create_log(
        db=db,
        action="ticket.create",
        resource_type="ticket",
        resource_id=getattr(result, "id", None),
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=request_http.headers.get("x-forwarded-for")
        or (request_http.client.host if request_http.client else None),
        user_agent=request_http.headers.get("user-agent"),
        request_method=request_http.method,
        request_path=request_http.url.path,
    )
    return result


@router.get("/", response_model=List[TicketResponse], status_code=status.HTTP_200_OK)
def get_all_tickets(
    db: db_dependency,
    user: admin_dependency,
    request: Request,
):
    rows = TicketService(db).get_tickets_with_messages()
    AuditLogService().create_log(
        db=db,
        action="ticket.list_all",
        resource_type="ticket",
        resource_id=None,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return rows


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ticket(
    db: db_dependency, user: admin_dependency, ticket_id: int, request: Request
):
    result = TicketService(db).delete_ticket(ticket_id)
    AuditLogService().create_log(
        db=db,
        action="ticket.delete",
        resource_type="ticket",
        resource_id=ticket_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_204_NO_CONTENT,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result


@router.get(
    "/user",
    response_model=List[TicketResponse],
    status_code=status.HTTP_200_OK,
)
def get_user_tickets(db: db_dependency, user: user_dependency, request: Request):
    rows = TicketService(db).get_user_tickets(user.get("id"))
    AuditLogService().create_log(
        db=db,
        action="ticket.list_user",
        resource_type="ticket",
        resource_id=None,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return rows


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
    request: Request,
):
    result = TicketService(db).add_message(
        ticket_id, user.get("id"), message_request.message
    )
    AuditLogService().create_log(
        db=db,
        action="ticket.message_added",
        resource_type="ticket",
        resource_id=ticket_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_201_CREATED,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
)
def update_ticket(
    db: db_dependency,
    user: admin_dependency,
    ticket_request: TicketUpdate,
    ticket_id: int,
    request: Request,
):
    result = TicketService(db).update_ticket(
        ticket_id,
        ticket_request,
    )
    AuditLogService().create_log(
        db=db,
        action="ticket.update",
        resource_type="ticket",
        resource_id=ticket_id,
        user_id=user.get("id"),
        changes=ticket_request.model_dump(exclude_unset=True),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
)
def get_ticket_with_messages(
    db: db_dependency,
    user: user_dependency,
    ticket_id: int,
    request: Request,
):
    result = TicketService(db).get_ticket_with_messages(ticket_id)
    AuditLogService().create_log(
        db=db,
        action="ticket.get_with_messages",
        resource_type="ticket",
        resource_id=ticket_id,
        user_id=user.get("id"),
        status="success",
        status_code=status.HTTP_200_OK,
        ip_address=request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_method=request.method,
        request_path=request.url.path,
    )
    return result
