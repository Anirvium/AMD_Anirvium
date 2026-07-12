from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.capability import CapabilityRoute, DirectCapabilityResult


ExecutionMode = Literal["policy_driven", "plan_driven", "autonomous", "hybrid"]
ConversationKind = Literal[
    "GREETING",
    "SMALL_TALK",
    "SUPPORT_QUERY",
    "FOLLOW_UP",
    "COMPLAINT",
    "ESCALATION_REQUEST",
    "CONFIRMATION",
    "CONVERSATION_END",
]


class ConversationTurn(BaseModel):
    turn_id: str
    role: Literal["customer", "agent", "system"]
    content: str
    created_at: str
    delivery_status: str = "recorded"


class ConversationSignal(BaseModel):
    conversation_id: str
    message_type: ConversationKind
    requires_agent_run: bool
    is_follow_up: bool = False
    topic_changed: bool = False
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    response: Optional[str] = None


class EmotionSignal(BaseModel):
    primary_emotion: str
    intensity: float = Field(ge=0.0, le=1.0)
    irritation_detected: bool
    repeat_contact_contribution: float = Field(ge=0.0, le=1.0)
    requires_acknowledgement: bool
    requires_apology: bool
    escalation_risk: float = Field(ge=0.0, le=1.0)
    signals: List[str] = Field(default_factory=list)


class CustomerContext(BaseModel):
    customer_id: str
    customer_name: str
    plan: str
    region: str = "unknown"
    preferred_channel: str = "chat"
    identity_status: str = "unknown"
    crm_account_id: Optional[str] = None
    open_case_ids: List[str] = Field(default_factory=list)
    interaction_count: int = 0


class RecontactAnalysis(BaseModel):
    customer_id: str
    current_issue: str
    related_cases: List[str] = Field(default_factory=list)
    contacts_last_24_hours: int = 0
    contacts_last_7_days: int = 0
    contacts_last_14_days: int = 0
    contacts_last_30_days: int = 0
    recontact_detected: bool = False
    previous_commitment_missed: bool = False
    semantic_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_action: str = "continue_standard_support"


class ToolExecution(BaseModel):
    tool_execution_id: str
    tool_name: str
    operation: str
    access_type: Literal["read", "write"]
    status: Literal["success", "failed", "approval_required", "reused"]
    authorization: str
    role: str
    idempotency_key: str
    attempt: int = 1
    timeout_ms: int = 3000
    latency_ms: int = 0
    approval_required: bool = False
    audit_id: str
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    simulated: bool = True


class AssuranceCommitment(BaseModel):
    assurance_given: bool
    assurance_type: Literal["action", "ownership", "process", "time_bound", "outcome_guarantee", "none"]
    assurance_text: str
    supported_by: List[str] = Field(default_factory=list)
    deadline: Optional[str] = None
    commitment_owner: Optional[str] = None
    approval_required: bool = False
    fulfilment_status: str = "not_applicable"


class EscalationEvent(BaseModel):
    escalation_id: str
    reason: str
    severity: str
    destination: str
    sla_minutes: int
    supporting_evidence: List[str] = Field(default_factory=list)
    status: Literal[
        "NOT_REQUIRED",
        "RECOMMENDED",
        "APPROVAL_REQUIRED",
        "ESCALATED",
        "ACCEPTED",
        "IN_PROGRESS",
        "RESOLVED",
        "REJECTED",
        "EXPIRED",
    ] = "NOT_REQUIRED"


class IncidentCluster(BaseModel):
    incident_id: Optional[str] = None
    issue_signature: str
    unique_customers: int
    window_minutes: int = 60
    threshold: int = 5
    detected: bool = False
    severity: str = "none"
    status: str = "not_triggered"
    linked_cases: List[str] = Field(default_factory=list)
    recommended_action: str = "monitor"


class SatisfactionSignal(BaseModel):
    predicted_satisfaction: float = Field(ge=0.0, le=1.0)
    predicted_label: str
    explicit_csat: Optional[int] = Field(default=None, ge=1, le=5)
    explicit_resolution: Optional[Literal["yes", "partially", "no"]] = None
    resolution_status: str
    customer_effort_score: float = Field(ge=0.0, le=1.0)
    dissatisfaction_reasons: List[str] = Field(default_factory=list)
    rubric: Dict[str, float] = Field(default_factory=dict)


class ProvenanceSource(BaseModel):
    source_id: str
    title: str
    section: Optional[str] = None
    version: str = "demo-v1"
    category: str = "knowledge"


class ProvenanceRecord(BaseModel):
    response_id: str
    sources: List[ProvenanceSource] = Field(default_factory=list)
    tool_executions: List[ToolExecution] = Field(default_factory=list)
    answer_confidence: float = Field(ge=0.0, le=1.0)
    customer_view: str
    auditor_view: str


class ResponseQualityGateResult(BaseModel):
    decision: Literal["approved", "rewritten", "human_review_required"]
    passed: bool
    checks: Dict[str, bool] = Field(default_factory=dict)
    score: float = Field(ge=0.0, le=1.0)
    original_length: int = 0
    final_length: int = 0
    rewrite_applied: bool = False
    blocking_reasons: List[str] = Field(default_factory=list)


class ExecutionStrategy(BaseModel):
    execution_mode: ExecutionMode
    decision_authority: str
    policy_guardian: str = "deterministic_policy_and_compliance_gates"
    autonomous_scope: List[str] = Field(default_factory=list)
    mandatory_capabilities: List[str] = Field(default_factory=list)
    selected_tools: List[str] = Field(default_factory=list)
    stop_conditions: List[str] = Field(default_factory=list)
    maximum_agent_steps: int = 13
    replan_limit: int = 1
    recalled_intelligence_ids: List[str] = Field(default_factory=list)
    memory_influenced_decisions: List[str] = Field(default_factory=list)
    autonomous_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    termination_reason: str = "governed_plan_committed"


class TrajectoryEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: str
    conversation_id: str
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    actor: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ChatTranscript(BaseModel):
    transcript_id: str
    conversation_id: str
    customer_id: str
    started_at: str
    ended_at: str
    turns: List[ConversationTurn]
    detected_issue: str
    customer_intent: str
    emotion_timeline: List[EmotionSignal] = Field(default_factory=list)
    previous_related_cases: List[str] = Field(default_factory=list)
    knowledge_sources_used: List[str] = Field(default_factory=list)
    tools_called: List[str] = Field(default_factory=list)
    assurances: List[AssuranceCommitment] = Field(default_factory=list)
    escalation: Optional[EscalationEvent] = None
    resolution_status: str
    unresolved_questions: List[str] = Field(default_factory=list)
    satisfaction: SatisfactionSignal
    follow_up_owner: Optional[str] = None
    redaction_status: str = "synthetic_data_no_pii"


class SarvagunExecution(BaseModel):
    system_name: str = "Sarvagun"
    platform: str = "Anirvium AI"
    conversation: ConversationSignal
    execution_strategy: ExecutionStrategy
    customer_context: CustomerContext
    emotion: EmotionSignal
    recontact: RecontactAnalysis
    tool_executions: List[ToolExecution] = Field(default_factory=list)
    assurances: List[AssuranceCommitment] = Field(default_factory=list)
    escalation: EscalationEvent
    incident: IncidentCluster
    satisfaction: SatisfactionSignal
    response_quality_gate: ResponseQualityGateResult
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    transcript: ChatTranscript
    resolution_stage: str = "closed"


class SuperTuriyaIntelligence(BaseModel):
    system_name: str = "SuperTuriya"
    platform: str = "Anirvium AI"
    observed_system: str = "Sarvagun"
    role: str = "core_trajectory_intelligence"
    lifecycle: List[str]
    trace_count: int
    event_count: int
    events: List[TrajectoryEvent] = Field(default_factory=list)
    discovered_path: List[str] = Field(default_factory=list)
    successes: List[str] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)
    intelligence: List[str] = Field(default_factory=list)
    improvement_recommendation_ids: List[str] = Field(default_factory=list)
    recalled_memory_ids: List[str] = Field(default_factory=list)
    applied_memory_ids: List[str] = Field(default_factory=list)
    created_memory_ids: List[str] = Field(default_factory=list)
    feedback_loop_status: str = "closed"
    automatic_policy_mutation: bool = False


class ConversationTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None


class ConversationTurnResponse(BaseModel):
    signal: ConversationSignal
    customer: Optional[CustomerContext] = None
    turns: List[ConversationTurn] = Field(default_factory=list)
    capability_route: Optional[CapabilityRoute] = None
    direct_result: Optional[DirectCapabilityResult] = None


class SatisfactionFeedbackRequest(BaseModel):
    run_id: str
    explicit_csat: int = Field(ge=1, le=5)
    explicit_resolution: Literal["yes", "partially", "no"]
