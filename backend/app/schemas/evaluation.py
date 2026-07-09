from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    task_completion: float = Field(ge=0.0, le=1.0)
    evidence_grounding: float = Field(ge=0.0, le=1.0)
    policy_compliance: float = Field(ge=0.0, le=1.0)
    hallucination_risk: float = Field(ge=0.0, le=1.0)
    escalation_quality: float = Field(ge=0.0, le=1.0)
    actionability: float = Field(ge=0.0, le=1.0)
    missing_information: float = Field(ge=0.0, le=1.0)
    customer_tone: float = Field(ge=0.0, le=1.0)
    token_efficiency: float = Field(ge=0.0, le=1.0)
    latency_efficiency: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=100.0)


class DiagnosisItem(BaseModel):
    category: str
    severity: str
    ticket_id: str | None = None
    message: str
    evidence_ids: List[str] = Field(default_factory=list)
    suggested_fix: str
    failure_type: str = ""
    affected_agent: str = ""
    business_impact: str = ""
    recommended_fix: str = ""
    metric_impact: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class OptimizationRecommendation(BaseModel):
    recommendation_id: str
    title: str
    change_type: str
    rationale: str
    expected_impact: str
    before: str
    after: str
    related_ticket_ids: List[str] = Field(default_factory=list)
    priority: str = "MEDIUM"
    target_agent: str = ""
    problem: str = ""
    root_cause: str = ""
    fix: str = ""
    expected_metric_lift: Dict[str, str] = Field(default_factory=dict)
    implementation_hint: str = ""


class EvaluationReport(BaseModel):
    run_id: str
    metrics: EvaluationMetrics
    diagnosis: List[DiagnosisItem]
    recommendations: List[OptimizationRecommendation]
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
