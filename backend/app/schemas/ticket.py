from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


PlanType = Literal["free", "pro", "business", "enterprise"]
TicketPriority = Literal["low", "medium", "high", "critical"]


class SupportTicket(BaseModel):
    ticket_id: str
    customer_id: str
    customer_name: str
    plan: PlanType
    issue_type: str
    priority: TicketPriority
    message: str
    created_at: str
    sla_deadline: str
    sentiment: str
    previous_interactions: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    expected_evidence_ids: List[str] = Field(default_factory=list)


class TicketQueueResponse(BaseModel):
    tickets: List[SupportTicket]

