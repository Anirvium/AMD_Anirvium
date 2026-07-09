from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.evaluation import EvaluationReport
from app.schemas.trajectory import TrajectoryGraph, TrajectorySpan
from app.schemas.visual_evidence import VisualEvidenceCard


RunSelectionMode = Literal["all_high_priority", "all", "selected"]
RunDataset = Literal["enterprise_saas", "customer_support"]


class RunRequest(BaseModel):
    selection_mode: RunSelectionMode = "all_high_priority"
    selected_ticket_ids: Optional[List[str]] = None
    dataset: RunDataset = "enterprise_saas"
    customer_query: Optional[str] = None


class FinalAction(BaseModel):
    ticket_id: str
    customer_name: str
    recommended_escalation: str
    owner: str
    urgency: str
    approval_state: str
    draft_response: str
    evidence_ids: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    next_action: str


class RunResult(BaseModel):
    run_id: str
    status: str
    selected_ticket_ids: List[str]
    final_actions: List[FinalAction]
    visual_evidence_cards: List[VisualEvidenceCard] = Field(default_factory=list)
    trajectory: List[TrajectorySpan]
    graph: TrajectoryGraph
    evaluation: EvaluationReport
    metadata: Dict[str, Any] = Field(default_factory=dict)
