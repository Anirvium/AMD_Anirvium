from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.cx import ExecutionMode, SarvagunExecution, SuperTuriyaIntelligence
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
    execution_mode: ExecutionMode = "hybrid"
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    explicit_csat: Optional[int] = Field(default=None, ge=1, le=5)
    explicit_resolution: Optional[Literal["yes", "partially", "no"]] = None
    correlation_id: Optional[str] = Field(default=None, min_length=6, max_length=128)


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
    confidence_score: float = Field(default=0.86, ge=0.0, le=1.0)
    compliance_status: str = "NOT_CHECKED"
    human_escalation_required: bool = False
    handoff_team: Optional[str] = None
    handoff_reason: Optional[str] = None
    handoff_summary: Optional[str] = None
    generation_source: str = "deterministic_safe_fallback"
    generation_model: Optional[str] = None
    fallback_reason: Optional[str] = None


class RunResult(BaseModel):
    run_id: str
    status: str
    selected_ticket_ids: List[str]
    final_actions: List[FinalAction]
    visual_evidence_cards: List[VisualEvidenceCard] = Field(default_factory=list)
    trajectory: List[TrajectorySpan]
    graph: TrajectoryGraph
    evaluation: EvaluationReport
    sarvagun: Optional[SarvagunExecution] = None
    superturiya: Optional[SuperTuriyaIntelligence] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    submitted_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[RunResult] = None
    error: Optional[str] = None
    current_step: int = Field(default=0, ge=0)
    total_steps: int = Field(default=13, ge=1)
    current_agent: Optional[str] = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    progress_message: Optional[str] = None
    correlation_id: Optional[str] = None
