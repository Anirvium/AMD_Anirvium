from fastapi import APIRouter, Query

from app.schemas.ticket import TicketQueueResponse
from app.services.data_loader import load_tickets


router = APIRouter(tags=["tickets"])


@router.get("/tickets", response_model=TicketQueueResponse)
def get_tickets(dataset: str = Query("enterprise_saas")) -> TicketQueueResponse:
    return TicketQueueResponse(tickets=load_tickets(dataset))
