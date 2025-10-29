from sqlalchemy.orm import Session, joinedload
from starlette.status import HTTP_404_NOT_FOUND
from app.config import settings
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket import TicketMessage
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.schemas.ticket import MessageCreate
from fastapi import HTTPException
from app.services.notifications import send_email


class TicketService:

    def __init__(self, db: Session):
        self.db = db

    def create_ticket(self, ticket_data: TicketCreate, user_id: int):
        ticket = Ticket(title=ticket_data.title, user_id=user_id, status="open")
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def add_message(self, ticket_id: int, user_id: int, message: str):
        ticket = (
            self.db.query(Ticket)
            .options(joinedload(Ticket.user))
            .filter(Ticket.id == ticket_id)
            .first()
        )

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket_message = TicketMessage(
            ticket_id=ticket_id,
            sender_id=user_id,
            message=message,
        )

        sender = self.db.query(User).filter(User.id == user_id).first()

        ticket.status = TicketStatus.IN_PROGRESS
        self.db.add(ticket_message)
        self.db.commit()
        self.db.refresh(ticket_message)
        self.db.refresh(ticket)
        if sender.role == "admin":
            send_email(ticket.user.email, ticket.title, ticket_message.message)
        else:
            send_email(settings.EMAIL_FROM, ticket.title, ticket_message.message)
        return ticket_message

    def get_ticket_with_messages(self, ticket_id: int):
        ticket = (
            self.db.query(Ticket)
            .options(
                joinedload(Ticket.messages), joinedload(Ticket.user)
            )  # ✅ Load messages
            .filter(Ticket.id == ticket_id)
            .first()
        )
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket

    def get_tickets_with_messages(self):
        tickets = self.db.query(Ticket).options(joinedload(Ticket.messages)).all()
        if not tickets:
            raise HTTPException(status_code=404, detail="Tickets not found")
        return tickets

    def get_user_tickets(self, user_id: int):
        return self.db.query(Ticket).filter(Ticket.user_id == user_id).all()

    def get_messages(self, ticket_id: int):
        return (
            self.db.query(TicketMessage)
            .options(joinedload(Ticket.messages), joinedload(Ticket.user))
            .filter(TicketMessage.ticket_id == ticket_id)
            .all()
        )

    def delete_ticket(self, ticket_id):
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Ticket not found"
            )
        self.db.delete(ticket)
        self.db.commit()

    def update_ticket(self, ticket_id: int, ticket_update: TicketUpdate):
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        if ticket_update.title is not None:
            ticket.title = ticket_update.title
        if ticket_update.status is not None:
            ticket.status = ticket_update.status  # ✅ enum

        self.db.commit()
        self.db.refresh(ticket)
        return ticket
