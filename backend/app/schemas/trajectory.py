from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalState(str, Enum):
    DRAFT_RECOMMENDATION = "DRAFT_RECOMMENDATION"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISED = "REVISED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"


class TrajectorySpan(BaseModel):
    run_id: str
    step_id: str
    parent_step_id: Optional[str] = None
    agent_name: str
    input_summary: str
    output_summary: str
    full_output: Dict[str, Any]
    tools_used: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    model_name: str = "mock-trajectory-model"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    risk_flags: List[str] = Field(default_factory=list)
    approval_state: ApprovalState = ApprovalState.DRAFT_RECOMMENDATION
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrajectoryGraphNode(BaseModel):
    id: str
    label: str
    status: str
    score: float = Field(ge=0.0, le=1.0)
    risk_flags: List[str] = Field(default_factory=list)


class TrajectoryGraphEdge(BaseModel):
    source: str
    target: str
    label: str


class TrajectoryGraph(BaseModel):
    nodes: List[TrajectoryGraphNode]
    edges: List[TrajectoryGraphEdge]


class TrajectoryResponse(BaseModel):
    run_id: str
    spans: List[TrajectorySpan]
    graph: TrajectoryGraph

