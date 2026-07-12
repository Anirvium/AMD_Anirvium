from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


CapabilityName = Literal[
    "support_case_execution",
    "customer_directory",
    "payment_failure_cases",
    "customer_lookup",
    "case_directory",
    "case_lookup",
    "support_analytics",
    "general_knowledge",
    "conversation_fast_path",
]

CapabilityExecutionPath = Literal[
    "sarvagun_agent_pipeline",
    "direct_relational_read",
    "deterministic_analytics",
    "general_knowledge_llm",
    "conversation_manager",
]


class CapabilityRoute(BaseModel):
    route_id: str
    capability: CapabilityName
    execution_path: CapabilityExecutionPath
    requires_agent_run: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    matched_signals: List[str] = Field(default_factory=list)
    read_only: bool = True
    data_scope: str = "none"
    event_type: str = "capability.routed"
    observed_by: str = "SuperTuriya"


class DirectCapabilityResult(BaseModel):
    capability: CapabilityName
    status: Literal["success", "not_found", "degraded"]
    answer: str
    record_count: int = 0
    records: List[Dict[str, Any]] = Field(default_factory=list)
    aggregates: Dict[str, Any] = Field(default_factory=dict)
    source_ids: List[str] = Field(default_factory=list)
    generated_by: str
    fallback_reason: Optional[str] = None
    synthetic_data_only: bool = True
