from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, List
from uuid import uuid4

from app.schemas.cx import (
    AssuranceCommitment,
    ChatTranscript,
    ConversationSignal,
    ConversationTurn,
    CustomerContext,
    EmotionSignal,
    EscalationEvent,
    ExecutionStrategy,
    IncidentCluster,
    ProvenanceRecord,
    ProvenanceSource,
    RecontactAnalysis,
    ResponseQualityGateResult,
    SarvagunExecution,
    SatisfactionSignal,
    SuperTuriyaIntelligence,
    ToolExecution,
    TrajectoryEvent,
)
from app.services.conversation import conversation_manager
from app.services.customer_connectors import tool_executor
from app.services.data_loader import load_cx_context
from app.services.memory import add_long_term_memory, add_mid_term_summary, add_short_term_memory
from app.services.observability import observability_context


_INCIDENT_LOCK = Lock()
_INCIDENT_EVENTS: List[Dict[str, Any]] = []
_INCIDENT_SEEDED = False
_OPERATIONS_LOCK = Lock()
_OPERATIONS: List[Dict[str, Any]] = []
_EXPLICIT_FEEDBACK: Dict[str, Dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


class EmotionAnalyzer:
    def analyze(self, message: str, *, static_sentiment: str, repeat_contacts: int) -> EmotionSignal:
        normalized = message.lower()
        signals: List[str] = []
        emotion = "neutral"
        intensity = 0.24

        if any(term in normalized for term in ("angry", "unacceptable", "terrible", "legal", "lawyer")):
            emotion = "anger"
            intensity = 0.9
            signals.append("explicit_anger_or_legal_language")
        elif any(term in normalized for term in ("frustrated", "again", "third contact", "nobody replied", "still not")):
            emotion = "frustration"
            intensity = 0.82
            signals.append("frustration_or_repeated_contact_language")
        elif any(term in normalized for term in ("worried", "anxious", "urgent", "immediately", "today")):
            emotion = "anxiety"
            intensity = 0.7
            signals.append("urgency_or_anxiety_language")
        elif any(term in normalized for term in ("confused", "do not understand", "don't understand")):
            emotion = "confusion"
            intensity = 0.58
            signals.append("confusion_language")
        elif static_sentiment in {"angry", "frustrated", "urgent"}:
            emotion = "frustration" if static_sentiment != "urgent" else "anxiety"
            intensity = 0.66
            signals.append("ticket_sentiment")

        repeat_contribution = _clamp(0.25 * repeat_contacts)
        if repeat_contacts >= 2:
            signals.append("repeat_contact_history")
            intensity = max(intensity, 0.78)
            if emotion == "neutral":
                emotion = "frustration"

        irritation = emotion in {"anger", "frustration"} or intensity >= 0.78
        escalation_risk = _clamp((intensity * 0.62) + (repeat_contribution * 0.38))
        return EmotionSignal(
            primary_emotion=emotion,
            intensity=_clamp(intensity),
            irritation_detected=irritation,
            repeat_contact_contribution=repeat_contribution,
            requires_acknowledgement=intensity >= 0.5 or repeat_contacts > 0,
            requires_apology=irritation or repeat_contacts >= 2,
            escalation_risk=escalation_risk,
            signals=signals,
        )


class RecontactDetector:
    def analyze(
        self,
        customer_id: str,
        issue_type: str,
        cases: List[Dict[str, Any]],
        *,
        reference_time: str | None = None,
    ) -> RecontactAnalysis:
        related = [case for case in cases if case.get("issue_type") == issue_type]
        missed = any(case.get("commitment_met") is False for case in related)
        now = _now()
        if reference_time:
            try:
                now = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
                if now.tzinfo is None:
                    now = now.replace(tzinfo=timezone.utc)
                now = now.astimezone(timezone.utc)
            except ValueError:
                now = _now()

        for case in related:
            raw = str(case.get("contacted_at", ""))
            if not raw:
                continue
            try:
                contacted_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if contacted_at.tzinfo is None:
                    contacted_at = contacted_at.replace(tzinfo=timezone.utc)
                now = max(now, contacted_at.astimezone(timezone.utc))
            except ValueError:
                continue

        def within(case: Dict[str, Any], days: int) -> bool:
            raw = str(case.get("contacted_at", ""))
            if not raw:
                return False
            try:
                contacted_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if contacted_at.tzinfo is None:
                    contacted_at = contacted_at.replace(tzinfo=timezone.utc)
            except ValueError:
                return False
            return timedelta(0) <= now - contacted_at.astimezone(timezone.utc) <= timedelta(days=days)

        contacts = len(related) + 1
        return RecontactAnalysis(
            customer_id=customer_id,
            current_issue=issue_type,
            related_cases=[str(case["case_id"]) for case in related],
            contacts_last_24_hours=sum(1 for case in related if within(case, 1)) + 1,
            contacts_last_7_days=sum(1 for case in related if within(case, 7)) + 1,
            contacts_last_14_days=sum(1 for case in related if within(case, 14)) + 1,
            contacts_last_30_days=sum(1 for case in related if within(case, 30)) + 1,
            recontact_detected=bool(related),
            previous_commitment_missed=missed,
            semantic_similarity=0.96 if related else 0.0,
            recommended_action="manager_or_senior_support_escalation" if len(related) >= 2 or missed else "attach_prior_case_history",
        )


class EmergingIncidentDetector:
    def __init__(self) -> None:
        self._seed()

    def _seed(self) -> None:
        global _INCIDENT_SEEDED
        with _INCIDENT_LOCK:
            if _INCIDENT_SEEDED:
                return
            now = _now()
            for item in load_cx_context().get("incident_seed", []):
                _INCIDENT_EVENTS.append(
                    {
                        **item,
                        "occurred_at": now - timedelta(minutes=int(item.get("minutes_ago", 0))),
                        "signature": self.signature(str(item.get("issue_type", "unknown"))),
                    }
                )
            _INCIDENT_SEEDED = True

    def signature(self, issue_type: str) -> str:
        return f"support:{issue_type}:in:web:v1"

    def observe(self, *, customer_id: str, case_id: str, issue_type: str) -> IncidentCluster:
        now = _now()
        signature = self.signature(issue_type)
        event_id = f"{customer_id}:{case_id}:{signature}"
        with _INCIDENT_LOCK:
            if not any(item.get("event_id") == event_id for item in _INCIDENT_EVENTS):
                _INCIDENT_EVENTS.append(
                    {
                        "event_id": event_id,
                        "customer_id": customer_id,
                        "case_id": case_id,
                        "issue_type": issue_type,
                        "signature": signature,
                        "occurred_at": now,
                    }
                )
            window_start = now - timedelta(minutes=60)
            matching = [
                item
                for item in _INCIDENT_EVENTS
                if item.get("signature") == signature and item.get("occurred_at", now) >= window_start
            ]
        unique_customers = sorted({str(item["customer_id"]) for item in matching})
        detected = len(unique_customers) > 5
        linked_cases = sorted({str(item.get("case_id")) for item in matching if item.get("case_id")})
        return IncidentCluster(
            incident_id=f"INC-{now.strftime('%Y%m%d')}-{int(hashlib.sha256(signature.encode('utf-8')).hexdigest()[:6], 16) % 1000:03d}" if detected else None,
            issue_signature=signature,
            unique_customers=len(unique_customers),
            window_minutes=60,
            threshold=5,
            detected=detected,
            severity="high" if detected else "none",
            status="investigating" if detected else "not_triggered",
            linked_cases=linked_cases,
            recommended_action="notify_incident_manager" if detected else "monitor",
        )


class HybridExecutionController:
    def build(
        self,
        *,
        requested_mode: str,
        issue_type: str,
        emotion: EmotionSignal,
        recontact: RecontactAnalysis,
        prior_memories: List[Dict[str, Any]],
    ) -> ExecutionStrategy:
        mode = requested_mode if requested_mode in {"policy_driven", "plan_driven", "autonomous", "hybrid"} else "hybrid"
        high_risk = issue_type in {
            "deposit_missing",
            "withdrawal_processed_missing",
            "verification_restriction",
            "cross_account_access",
            "priority_policy_exception",
            "bonus_dispute",
        }
        if mode == "policy_driven":
            authority = "deterministic_policy_workflow"
            autonomous_scope: List[str] = []
        elif mode == "plan_driven":
            authority = "planner_agent_executable_plan"
            autonomous_scope = ["response_language"]
        elif mode == "autonomous":
            authority = "bounded_sarvagun_autonomous_controller"
            autonomous_scope = ["task_decomposition", "tool_selection", "clarification", "response_composition"]
        else:
            authority = "autonomous_planning_inside_deterministic_guardrails" if not high_risk else "governed_plan_with_bounded_autonomy"
            autonomous_scope = ["tool_selection", "response_composition", "clarification"]

        selected_tools = ["mock_customer_system.get_open_cases", "mock_customer_system.get_interaction_history"]
        if issue_type in {"deposit_missing", "withdrawal_processed_missing", "bonus_dispute"}:
            selected_tools.append("mock_customer_system.lookup_operational_status")
        if recontact.recontact_detected or emotion.escalation_risk >= 0.6:
            selected_tools.append("mock_customer_system.create_escalation")
        if prior_memories:
            selected_tools.append("superturiya.trajectory_memory_search")

        recalled_ids = [str(item.get("id")) for item in prior_memories if item.get("id")]
        influenced = []
        if recalled_ids:
            influenced = [
                "review_prior_failure_patterns_before_planning",
                "extend_evidence_checklist_with_recalled_trajectory_intelligence",
            ]
        autonomous_decisions: List[Dict[str, Any]] = []
        if mode in {"autonomous", "hybrid"}:
            autonomous_decisions = [
                {
                    "iteration": 1,
                    "observation": {
                        "issue_type": issue_type,
                        "emotion_intensity": emotion.intensity,
                        "recontact": recontact.recontact_detected,
                    },
                    "decision": "select_allowlisted_context_and_domain_tools",
                    "selected_tools": selected_tools,
                    "policy_supervisor": "accepted",
                },
                {
                    "iteration": 2,
                    "observation": {"required_policy_gate": high_risk},
                    "decision": "commit_existing_agent_plan_inside_safety_envelope",
                    "policy_supervisor": "accepted",
                },
            ]
        return ExecutionStrategy(
            execution_mode=mode,
            decision_authority=authority,
            autonomous_scope=autonomous_scope,
            mandatory_capabilities=[
                "Planner Agent",
                "Knowledge Retrieval Agent",
                "Policy Checker Agent",
                "Response Drafting Agent",
                "Compliance Agent",
                "Critic / Evaluator Agent",
                "Reflection Agent",
                "Learning Extraction Agent",
                "Optimizer Agent",
            ],
            selected_tools=selected_tools,
            stop_conditions=[
                "unsupported_commitment_without_evidence",
                "policy_or_identity_bypass",
                "unauthorized_enterprise_write",
                "maximum_agent_steps_exceeded",
            ],
            recalled_intelligence_ids=recalled_ids,
            memory_influenced_decisions=influenced,
            autonomous_decisions=autonomous_decisions,
            termination_reason="bounded_plan_committed_before_agent_execution",
        )


class EscalationPolicyEngine:
    def evaluate(
        self,
        *,
        run_id: str,
        message: str,
        issue_type: str,
        emotion: EmotionSignal,
        recontact: RecontactAnalysis,
        incident: IncidentCluster,
    ) -> EscalationEvent:
        normalized = message.lower()
        reason = "standard_support_route"
        destination = "existing_support_owner"
        severity = "low"
        sla_minutes = 240
        status = "RECOMMENDED"

        if incident.detected:
            reason, destination, severity, sla_minutes, status = "multi_customer_incident", "incident_manager", "high", 15, "ESCALATED"
        elif any(term in normalized for term in ("manager", "supervisor")):
            reason, destination, severity, sla_minutes, status = "customer_requested_manager", "support_manager", "high", 15, "ESCALATED"
        elif emotion.primary_emotion == "anger" and any(term in normalized for term in ("legal", "lawyer")):
            reason, destination, severity, sla_minutes, status = "severe_anger_or_legal_threat", "senior_manager", "critical", 10, "ESCALATED"
        elif recontact.previous_commitment_missed or recontact.contacts_last_7_days >= 3:
            reason, destination, severity, sla_minutes, status = "repeat_contact_unresolved", "senior_support", "high", 30, "ESCALATED"
        elif issue_type in {"cross_account_access", "verification_restriction"}:
            reason, destination, severity, sla_minutes, status = "identity_or_security_control", "security_or_verification_team", "high", 30, "APPROVAL_REQUIRED"
        elif issue_type in {"deposit_missing", "withdrawal_processed_missing", "bonus_dispute"}:
            reason, destination, severity, sla_minutes, status = "financial_or_bonus_review", "finance_supervisor", "medium", 60, "APPROVAL_REQUIRED"
        elif issue_type == "priority_policy_exception":
            reason, destination, severity, sla_minutes, status = "policy_exception_requested", "authorized_approver", "high", 30, "APPROVAL_REQUIRED"

        return EscalationEvent(
            escalation_id=f"esc_{run_id[-12:]}",
            reason=reason,
            severity=severity,
            destination=destination,
            sla_minutes=sla_minutes,
            supporting_evidence=recontact.related_cases + incident.linked_cases,
            status=status,
        )


class AssurancePolicyEngine:
    def build(self, action: Dict[str, Any], note_tool: ToolExecution | None) -> AssuranceCommitment:
        if note_tool is None or note_tool.status not in {"success", "reused"}:
            return AssuranceCommitment(
                assurance_given=False,
                assurance_type="none",
                assurance_text="",
                supported_by=[],
                approval_required=False,
            )
        owner = str(action.get("owner") or "responsible support team")
        text = (
            f"I have documented the complete case history for {owner}. "
            "I cannot confirm the final outcome until the responsible team completes its evidence and approval checks."
        )
        return AssuranceCommitment(
            assurance_given=True,
            assurance_type="ownership",
            assurance_text=text,
            supported_by=list(action.get("evidence_ids", [])),
            commitment_owner=owner,
            approval_required=False,
            fulfilment_status="documented",
        )


class SatisfactionEvaluator:
    def evaluate(
        self,
        *,
        action: Dict[str, Any],
        emotion: EmotionSignal,
        recontact: RecontactAnalysis,
        assurance: AssuranceCommitment,
        explicit_csat: int | None,
        explicit_resolution: str | None,
    ) -> SatisfactionSignal:
        draft = str(action.get("draft_response", "")).lower()
        empathy = 1.0 if any(term in draft for term in ("understand", "sorry", "frustrating")) else 0.35
        acknowledgement = 1.0 if any(term in draft for term in ("understand", "i can see", "i'm sorry", "i am sorry")) else 0.4
        assurance_validity = 1.0 if (not assurance.assurance_given or bool(assurance.supported_by)) else 0.3
        actionability = 1.0 if action.get("owner") and action.get("next_action") else 0.35
        tone = 0.92 if not any(term in draft for term in ("your fault", "obviously", "calm down")) else 0.2
        effort = _clamp(0.25 + (0.22 if recontact.recontact_detected else 0.0) + (0.18 if recontact.previous_commitment_missed else 0.0))
        predicted = 0.82
        reasons: List[str] = []
        if recontact.recontact_detected:
            predicted -= 0.18
            reasons.append("repeat_contact")
        if recontact.previous_commitment_missed:
            predicted -= 0.16
            reasons.append("previous_commitment_missed")
        if action.get("human_escalation_required"):
            predicted -= 0.08
            reasons.append("issue_not_resolved_during_chat")
        if empathy < 0.8 and emotion.requires_acknowledgement:
            predicted -= 0.12
            reasons.append("insufficient_acknowledgement")
        predicted += 0.05 if assurance.assurance_given else 0.0
        predicted = _clamp(predicted)
        label = "satisfied" if predicted >= 0.78 else "partially_satisfied" if predicted >= 0.5 else "dissatisfied"
        resolution_status = "escalated" if action.get("human_escalation_required") else "draft_resolution_ready"
        rubric = {
            "correctness": 0.9 if action.get("evidence_ids") else 0.4,
            "evidence_grounding": 1.0 if action.get("evidence_ids") else 0.0,
            "empathy": empathy,
            "acknowledgement": acknowledgement,
            "assurance_validity": assurance_validity,
            "actionability": actionability,
            "tone": tone,
            "policy_compliance": 1.0 if action.get("compliance_status") != "BLOCKED" else 0.0,
            "completeness": 0.9 if action.get("next_action") else 0.5,
            "repetition": 0.92,
            "escalation_compliance": 1.0 if action.get("owner") else 0.3,
        }
        rubric["overall_quality"] = round(sum(rubric.values()) / len(rubric), 3)
        return SatisfactionSignal(
            predicted_satisfaction=predicted,
            predicted_label=label,
            explicit_csat=explicit_csat,
            explicit_resolution=explicit_resolution,
            resolution_status=resolution_status,
            customer_effort_score=effort,
            dissatisfaction_reasons=reasons,
            rubric=rubric,
        )


class ResponseQualityGate:
    """Deterministic pre-delivery safety and CX gate around the existing agents."""

    _UNSAFE_PROMISES = ("guaranteed", "definitely", "will be approved", "will be refunded", "will be unblocked")
    _PRIVATE_REASONING = ("<think>", "system prompt", "chain of thought", "hidden reasoning")

    def evaluate(
        self,
        *,
        action: Dict[str, Any],
        customer: CustomerContext,
        emotion: EmotionSignal,
        recontact: RecontactAnalysis,
        escalation: EscalationEvent,
        assurance: AssuranceCommitment,
        tools: List[ToolExecution],
    ) -> tuple[str, ResponseQualityGateResult]:
        original = str(action.get("draft_response", "")).strip()
        lowered = original.lower()
        escalation_written = any(
            tool.operation == "create_escalation" and tool.status in {"success", "reused"}
            for tool in tools
        )
        checks = {
            "evidence_grounded": bool(action.get("evidence_ids")),
            "policy_checked": action.get("compliance_status") in {"PASS", "REVIEW_REQUIRED"},
            "no_unsupported_outcome_guarantee": not any(term in lowered for term in self._UNSAFE_PROMISES),
            "no_private_reasoning": not any(term in lowered for term in self._PRIVATE_REASONING),
            "emotion_acknowledged": (not emotion.requires_acknowledgement) or any(
                term in lowered for term in ("understand", "sorry", "frustrat")
            ),
            "assurance_supported": (not assurance.assurance_given) or bool(assurance.supported_by),
            "escalation_claim_supported": escalation.status != "ESCALATED" or escalation_written,
            "concise_enough": 40 <= len(original) <= 900,
        }
        blocking = [name for name, passed in checks.items() if not passed]
        rewrite_needed = any(
            name in blocking
            for name in {
                "emotion_acknowledged",
                "concise_enough",
                "no_unsupported_outcome_guarantee",
                "no_private_reasoning",
            }
        ) or str(action.get("generation_source")) == "deterministic_safe_fallback"
        final = self._safe_compose(
            action=action,
            customer=customer,
            emotion=emotion,
            recontact=recontact,
            escalation=escalation,
            assurance=assurance,
            tools=tools,
        ) if rewrite_needed else original
        hard_blockers = [
            name for name in blocking if name in {"evidence_grounded", "policy_checked", "assurance_supported", "escalation_claim_supported"}
        ]
        decision = "human_review_required" if hard_blockers or action.get("approval_state") == "APPROVAL_REQUIRED" else "rewritten" if rewrite_needed else "approved"
        final_checks = dict(checks)
        final_lowered = final.lower()
        final_checks["no_unsupported_outcome_guarantee"] = not any(term in final_lowered for term in self._UNSAFE_PROMISES)
        final_checks["no_private_reasoning"] = not any(term in final_lowered for term in self._PRIVATE_REASONING)
        final_checks["emotion_acknowledged"] = (not emotion.requires_acknowledgement) or any(
            term in final_lowered for term in ("understand", "sorry", "frustrat")
        )
        final_checks["concise_enough"] = 40 <= len(final) <= 900
        score = round(sum(1 for passed in final_checks.values() if passed) / max(1, len(final_checks)), 3)
        return final, ResponseQualityGateResult(
            decision=decision,
            passed=all(final_checks.values()) and not hard_blockers,
            checks=final_checks,
            score=score,
            original_length=len(original),
            final_length=len(final),
            rewrite_applied=rewrite_needed,
            blocking_reasons=hard_blockers,
        )

    def _safe_compose(
        self,
        *,
        action: Dict[str, Any],
        customer: CustomerContext,
        emotion: EmotionSignal,
        recontact: RecontactAnalysis,
        escalation: EscalationEvent,
        assurance: AssuranceCommitment,
        tools: List[ToolExecution],
    ) -> str:
        opening = (
            f"I’m sorry you’ve had to contact us again about this, {customer.customer_name}."
            if recontact.recontact_detected
            else f"I understand this needs a clear answer, {customer.customer_name}."
            if emotion.requires_acknowledgement
            else f"Hello {customer.customer_name}."
        )
        status_tool = next(
            (tool for tool in tools if tool.operation == "lookup_operational_status" and tool.status in {"success", "reused"}),
            None,
        )
        status = str((status_tool.result if status_tool else {}).get("status", "")).replace("_", " ").strip()
        checked = f"I checked the case history{f' and the current status is {status}' if status else ''}."
        escalation_tool = next(
            (tool for tool in tools if tool.operation == "create_escalation" and tool.status in {"success", "reused"}),
            None,
        )
        if escalation.status == "ESCALATED" and escalation_tool:
            action_sentence = (
                f"I created an escalation to {escalation.destination.replace('_', ' ')} with the related cases and policy evidence attached."
            )
        else:
            action_sentence = f"The next governed step is with {str(action.get('owner') or escalation.destination)}."
        limitation = assurance.assurance_text or "I cannot confirm the final outcome until the responsible team completes its evidence and approval checks."
        return " ".join((opening, checked, action_sentence, limitation))


class SarvagunLifecycle:
    def __init__(self) -> None:
        self.emotion_analyzer = EmotionAnalyzer()
        self.recontact_detector = RecontactDetector()
        self.incident_detector = EmergingIncidentDetector()
        self.execution_controller = HybridExecutionController()
        self.escalation_engine = EscalationPolicyEngine()
        self.assurance_engine = AssurancePolicyEngine()
        self.satisfaction_evaluator = SatisfactionEvaluator()
        self.response_quality_gate = ResponseQualityGate()

    def prepare(
        self,
        *,
        run_id: str,
        request: Any,
        tickets: List[Any],
        prior_memories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not tickets:
            raise ValueError("Sarvagun requires at least one valid support case")
        ticket = tickets[0]
        message = str(request.customer_query or ticket.message)
        conversation_id = str(request.conversation_id or f"conv_{run_id[-12:]}")
        session = conversation_manager.get_session(conversation_id)
        session_turns = list((session or {}).get("turns", []))
        last_turn = session_turns[-1] if session_turns else None
        current_turn_already_recorded = bool(
            last_turn
            and last_turn.get("role") == "customer"
            and str(last_turn.get("content", "")).strip() == message.strip()
        )
        if not current_turn_already_recorded:
            turn_result = conversation_manager.handle_turn(
                message,
                conversation_id=conversation_id,
                customer_id=str(getattr(request, "customer_id", None) or ticket.customer_id),
            )
            conversation = turn_result.signal
        else:
            conversation = conversation_manager.analyze(
                message,
                conversation_id=conversation_id,
                has_support_history=bool(session and session.get("has_support_history")),
            )

        customer_tool = tool_executor.execute(
            "find_customer",
            ticket.customer_id,
            idempotency_key=f"{run_id}:find_customer:{ticket.customer_id}",
        )
        cases_tool = tool_executor.execute(
            "get_open_cases",
            ticket.customer_id,
            idempotency_key=f"{run_id}:open_cases:{ticket.customer_id}",
        )
        history_tool = tool_executor.execute(
            "get_interaction_history",
            ticket.customer_id,
            idempotency_key=f"{run_id}:history:{ticket.customer_id}",
        )
        tool_executions = [customer_tool, cases_tool, history_tool]

        customer_data = customer_tool.result or {
            "customer_id": ticket.customer_id,
            "customer_name": ticket.customer_name,
            "plan": ticket.plan,
        }
        open_cases = cases_tool.result.get("records", []) if isinstance(cases_tool.result, dict) else []
        history = history_tool.result.get("records", []) if isinstance(history_tool.result, dict) else []
        customer = CustomerContext(
            customer_id=str(customer_data.get("customer_id", ticket.customer_id)),
            customer_name=str(customer_data.get("customer_name", ticket.customer_name)),
            plan=str(customer_data.get("plan", ticket.plan)),
            region=str(customer_data.get("region", "unknown")),
            preferred_channel=str(customer_data.get("preferred_channel", "chat")),
            identity_status=str(customer_data.get("identity_status", "unknown")),
            crm_account_id=customer_data.get("crm_account_id"),
            open_case_ids=[str(item.get("case_id")) for item in open_cases],
            interaction_count=len(history),
        )
        recontact = self.recontact_detector.analyze(
            ticket.customer_id,
            ticket.issue_type,
            history,
            reference_time=str(getattr(ticket, "created_at", "") or ""),
        )
        emotion = self.emotion_analyzer.analyze(
            message,
            static_sentiment=str(ticket.sentiment),
            repeat_contacts=len(recontact.related_cases),
        )
        incident = self.incident_detector.observe(
            customer_id=ticket.customer_id,
            case_id=ticket.ticket_id,
            issue_type=ticket.issue_type,
        )
        strategy = self.execution_controller.build(
            requested_mode=str(request.execution_mode),
            issue_type=ticket.issue_type,
            emotion=emotion,
            recontact=recontact,
            prior_memories=prior_memories,
        )
        if "mock_customer_system.lookup_operational_status" in strategy.selected_tools:
            status_tool = tool_executor.execute(
                "lookup_operational_status",
                ticket.issue_type,
                idempotency_key=f"{run_id}:status:{ticket.issue_type}",
            )
            tool_executions.append(status_tool)
        escalation = self.escalation_engine.evaluate(
            run_id=run_id,
            message=message,
            issue_type=ticket.issue_type,
            emotion=emotion,
            recontact=recontact,
            incident=incident,
        )
        events = [
            self._event("conversation.started", conversation_id, run_id, "Sarvagun", {"execution_mode": strategy.execution_mode}),
            self._event("message.received", conversation_id, run_id, "customer", {"message_type": conversation.message_type}),
            self._event("emotion.detected", conversation_id, run_id, "Sarvagun", emotion.model_dump()),
        ]
        capability_routes = list((session or {}).get("capability_routes", []))
        if capability_routes:
            events.append(
                self._event(
                    "capability.routed",
                    conversation_id,
                    run_id,
                    "SuperTuriya",
                    capability_routes[-1],
                )
            )
        if strategy.recalled_intelligence_ids:
            events.append(
                self._event(
                    "memory.recalled",
                    conversation_id,
                    run_id,
                    "SuperTuriya",
                    {
                        "memory_ids": strategy.recalled_intelligence_ids,
                        "accepted_influences": strategy.memory_influenced_decisions,
                        "policy_override_allowed": False,
                    },
                )
            )
        if recontact.recontact_detected:
            events.append(self._event("recontact.detected", conversation_id, run_id, "Sarvagun", recontact.model_dump()))
        if incident.detected:
            events.append(self._event("incident.detected", conversation_id, run_id, "Sarvagun", incident.model_dump()))
        for tool in tool_executions:
            events.append(
                self._event(
                    "tool.called",
                    conversation_id,
                    run_id,
                    tool.tool_name,
                    {
                        "tool_execution_id": tool.tool_execution_id,
                        "operation": tool.operation,
                        "access_type": tool.access_type,
                        "authorization": tool.authorization,
                        "idempotency_key": tool.idempotency_key,
                    },
                )
            )
            events.append(self._event("tool.completed", conversation_id, run_id, tool.tool_name, tool.model_dump()))
        if strategy.autonomous_decisions:
            strategy.autonomous_decisions[0]["executed_tool_ids"] = [
                tool.tool_execution_id for tool in tool_executions if tool.tool_name in strategy.selected_tools
            ]
            strategy.autonomous_decisions[0]["mandatory_context_tool_ids"] = [
                tool.tool_execution_id for tool in tool_executions if tool.tool_name not in strategy.selected_tools
            ]
            strategy.autonomous_decisions[0]["observed_tool_statuses"] = {
                tool.operation: tool.status for tool in tool_executions
            }

        return {
            "conversation_signal": conversation,
            "customer_context": customer,
            "recontact_analysis": recontact,
            "emotion_signal": emotion,
            "incident_cluster": incident,
            "execution_strategy": strategy,
            "cx_escalation": escalation,
            "enterprise_tool_executions": tool_executions,
            "assurance_commitments": [],
            "response_quality_gates": [],
            "trajectory_events": events,
        }

    def after_agent(self, agent_name: str, context: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        if agent_name == "Planner Agent":
            strategy: ExecutionStrategy = context["execution_strategy"]
            output["execution_strategy"] = strategy.model_dump()
            output.setdefault("tools_used", []).extend(
                ["sarvagun.hybrid_execution_controller"] + (["superturiya.memory_guidance"] if strategy.recalled_intelligence_ids else [])
            )
            context["trajectory_events"].append(
                self._event(
                    "plan.created",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    agent_name,
                    strategy.model_dump(),
                )
            )
        elif agent_name == "Knowledge Retrieval Agent":
            context["trajectory_events"].append(
                self._event(
                    "source.retrieved",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    agent_name,
                    {
                        "evidence_ids": list(output.get("evidence_ids", [])),
                        "source_count": len(output.get("evidence_ids", [])),
                    },
                )
            )
        elif agent_name == "Policy Checker Agent":
            context["trajectory_events"].append(
                self._event(
                    "policy.checked",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    agent_name,
                    {
                        "approval_state": output.get("approval_state"),
                        "risk_flags": output.get("risk_flags", []),
                    },
                )
            )
        elif agent_name == "Escalation Agent":
            self._apply_escalation(context, output)
        elif agent_name == "Response Drafting Agent":
            self._enhance_responses(context, output)
        elif agent_name == "Compliance Agent":
            self._finalize_response_quality(context)
            context["trajectory_events"].append(
                self._event(
                    "compliance.checked",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    agent_name,
                    {
                        "approval_state": output.get("approval_state"),
                        "risk_flags": output.get("risk_flags", []),
                    },
                )
            )
        return output

    def _apply_escalation(self, context: Dict[str, Any], output: Dict[str, Any]) -> None:
        event: EscalationEvent = context["cx_escalation"]
        if event.status != "ESCALATED":
            return
        for ticket_id, escalation in context.get("escalations", {}).items():
            if event.destination != "existing_support_owner":
                escalation["recommended_escalation"] = f"{escalation['recommended_escalation']} + {event.destination.replace('_', ' ').title()}"
                escalation["owner"] = event.destination.replace("_", " ").title() + " queue"
                escalation["next_action"] = f"{escalation['next_action']} CX policy requires {event.destination.replace('_', ' ')} within {event.sla_minutes} minutes."
            event.supporting_evidence = sorted(set(event.supporting_evidence + escalation.get("evidence_ids", [])))
            case_id = context["recontact_analysis"].related_cases[-1] if context["recontact_analysis"].related_cases else ticket_id
            tool = tool_executor.execute(
                "create_escalation",
                case_id,
                event.model_dump(),
                idempotency_key=f"{context['run_id']}:create_escalation:{case_id}:{event.reason}",
                approval_required=False,
            )
            context["enterprise_tool_executions"].append(tool)
            output.setdefault("tools_used", []).append(tool.tool_name)
            self._append_tool_events(context, tool)
            context["trajectory_events"].append(
                self._event(
                    "escalation.created",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    "Sarvagun escalation policy engine",
                    {**event.model_dump(), "tool_execution_id": tool.tool_execution_id, "tool_status": tool.status},
                )
            )
            strategy: ExecutionStrategy = context["execution_strategy"]
            if strategy.autonomous_decisions:
                decision = strategy.autonomous_decisions[-1]
                decision["observation"] = {
                    **dict(decision.get("observation", {})),
                    "escalation_reason": event.reason,
                    "destination": event.destination,
                    "policy_status": event.status,
                }
                decision["decision"] = "commit_governed_plan_and_execute_allowlisted_escalation"
                decision["executed_tool_ids"] = [tool.tool_execution_id]
                decision["observed_tool_statuses"] = {tool.operation: tool.status}
        output["escalations"] = context.get("escalations", {})

    def _enhance_responses(self, context: Dict[str, Any], output: Dict[str, Any]) -> None:
        emotion: EmotionSignal = context["emotion_signal"]
        recontact: RecontactAnalysis = context["recontact_analysis"]
        for action in context.get("final_actions", []):
            draft = str(action.get("draft_response", "")).strip()
            for marker in (" Internal evidence:", "Internal evidence:"):
                if marker in draft:
                    draft = draft.split(marker, 1)[0].strip() + " The case record includes the supporting evidence for review."
                    break
            if recontact.recontact_detected and not draft.lower().startswith("i’m sorry you’ve had to contact us again"):
                draft = "I’m sorry you’ve had to contact us again about the same issue. " + draft
            elif emotion.requires_acknowledgement and not any(term in draft.lower()[:180] for term in ("understand", "sorry", "frustrat")):
                draft = "I understand this situation needs a clear and careful response. " + draft

            case_id = recontact.related_cases[-1] if recontact.related_cases else action["ticket_id"]
            note_tool = tool_executor.execute(
                "add_case_note",
                case_id,
                f"Sarvagun prepared a governed response for {action['ticket_id']} with evidence {', '.join(action.get('evidence_ids', []))}.",
                idempotency_key=f"{context['run_id']}:case_note:{case_id}",
            )
            context["enterprise_tool_executions"].append(note_tool)
            self._append_tool_events(context, note_tool)
            assurance = self.assurance_engine.build(action, note_tool)
            context["assurance_commitments"].append(assurance)
            if assurance.assurance_given and assurance.assurance_text.lower() not in draft.lower():
                draft = f"{draft} {assurance.assurance_text}"
            action["draft_response"] = draft
            final_draft, _ = self.response_quality_gate.evaluate(
                action=action,
                customer=context["customer_context"],
                emotion=emotion,
                recontact=recontact,
                escalation=context["cx_escalation"],
                assurance=assurance,
                tools=context["enterprise_tool_executions"],
            )
            action["draft_response"] = final_draft
            output.setdefault("tools_used", []).append(note_tool.tool_name)
            context["trajectory_events"].append(
                self._event(
                    "assurance.created",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    "Sarvagun assurance policy engine",
                    assurance.model_dump(),
                )
            )
        output["final_actions"] = context.get("final_actions", [])

    def _finalize_response_quality(self, context: Dict[str, Any]) -> None:
        context["response_quality_gates"] = []
        assurances = list(context.get("assurance_commitments", []))
        for index, action in enumerate(context.get("final_actions", [])):
            assurance = assurances[index] if index < len(assurances) else AssuranceCommitment(
                assurance_given=False,
                assurance_type="none",
                assurance_text="",
            )
            final_draft, quality_gate = self.response_quality_gate.evaluate(
                action=action,
                customer=context["customer_context"],
                emotion=context["emotion_signal"],
                recontact=context["recontact_analysis"],
                escalation=context["cx_escalation"],
                assurance=assurance,
                tools=context["enterprise_tool_executions"],
            )
            action["draft_response"] = final_draft
            context["response_quality_gates"].append(quality_gate)
            context["trajectory_events"].append(
                self._event(
                    "response.quality_checked",
                    context["conversation_signal"].conversation_id,
                    context["run_id"],
                    "SuperTuriya response quality gate",
                    quality_gate.model_dump(),
                )
            )

    def finalize(self, *, context: Dict[str, Any], spans: List[Any], request: Any) -> tuple[SarvagunExecution, SuperTuriyaIntelligence]:
        action = context.get("final_actions", [{}])[0]
        assurance = (context.get("assurance_commitments") or [AssuranceCommitment(
            assurance_given=False,
            assurance_type="none",
            assurance_text="",
        )])[0]
        satisfaction = self.satisfaction_evaluator.evaluate(
            action=action,
            emotion=context["emotion_signal"],
            recontact=context["recontact_analysis"],
            assurance=assurance,
            explicit_csat=getattr(request, "explicit_csat", None),
            explicit_resolution=getattr(request, "explicit_resolution", None),
        )
        conversation_id = context["conversation_signal"].conversation_id
        response_text = str(action.get("draft_response", ""))
        if response_text:
            conversation_manager.record_agent_turn(conversation_id, response_text)
        session = conversation_manager.get_session(conversation_id)
        turns = [ConversationTurn(**turn) for turn in (session or {}).get("turns", [])]
        if not any(turn.role == "customer" for turn in turns):
            turns.insert(
                0,
                ConversationTurn(
                    turn_id=f"turn_{uuid4().hex[:10]}",
                    role="customer",
                    content=str(request.customer_query or context["tickets"][0].message),
                    created_at=_now_iso(),
                ),
            )
        sources = self._source_ids(context)
        transcript = ChatTranscript(
            transcript_id=f"TRANSCRIPT-{context['run_id']}",
            conversation_id=conversation_id,
            customer_id=context["customer_context"].customer_id,
            started_at=(session or {}).get("started_at", turns[0].created_at),
            ended_at=_now_iso(),
            turns=turns,
            detected_issue=str(context.get("resolved_intent") or context["tickets"][0].issue_type),
            customer_intent=context["conversation_signal"].message_type,
            emotion_timeline=[context["emotion_signal"]],
            previous_related_cases=context["recontact_analysis"].related_cases,
            knowledge_sources_used=sources,
            tools_called=[tool.tool_name for tool in context["enterprise_tool_executions"]],
            assurances=list(context.get("assurance_commitments", [])),
            escalation=context["cx_escalation"],
            resolution_status=satisfaction.resolution_status,
            unresolved_questions=[action.get("next_action")] if action.get("human_escalation_required") else [],
            satisfaction=satisfaction,
            follow_up_owner=action.get("owner"),
        )
        case_id = context["recontact_analysis"].related_cases[-1] if context["recontact_analysis"].related_cases else action.get("ticket_id", "unknown")
        transcript_tool = tool_executor.execute(
            "attach_transcript",
            case_id,
            transcript.model_dump(mode="json"),
            idempotency_key=f"{context['run_id']}:attach_transcript:{case_id}",
        )
        context["enterprise_tool_executions"].append(transcript_tool)
        self._append_tool_events(context, transcript_tool)
        transcript.tools_called.append(transcript_tool.tool_name)

        provenance = self._provenance(context, action)
        events = list(context["trajectory_events"])
        for span in spans:
            events.append(
                self._event(
                    "agent.completed",
                    conversation_id,
                    context["run_id"],
                    span.agent_name,
                    {"step_id": span.step_id, "tools": span.tools_used, "evidence_ids": span.evidence_ids, "confidence": span.confidence},
                )
            )
        events.extend(
            [
                self._event("response.drafted", conversation_id, context["run_id"], "Sarvagun", {"response_id": provenance[0].response_id if provenance else None}),
                self._event(
                    "response.ready_for_review",
                    conversation_id,
                    context["run_id"],
                    "SuperTuriya response quality gate",
                    (context.get("response_quality_gates") or [ResponseQualityGateResult(
                        decision="human_review_required",
                        passed=False,
                        score=0.0,
                        blocking_reasons=["response_not_evaluated"],
                    )])[0].model_dump(),
                ),
                self._event("conversation.closed", conversation_id, context["run_id"], "Sarvagun", {"resolution_status": satisfaction.resolution_status}),
                self._event("transcript.generated", conversation_id, context["run_id"], "SuperTuriya", {"transcript_id": transcript.transcript_id}),
            ]
        )
        sarvagun = SarvagunExecution(
            conversation=context["conversation_signal"],
            execution_strategy=context["execution_strategy"],
            customer_context=context["customer_context"],
            emotion=context["emotion_signal"],
            recontact=context["recontact_analysis"],
            tool_executions=context["enterprise_tool_executions"],
            assurances=context["assurance_commitments"],
            escalation=context["cx_escalation"],
            incident=context["incident_cluster"],
            satisfaction=satisfaction,
            response_quality_gate=(context.get("response_quality_gates") or [ResponseQualityGateResult(
                decision="human_review_required",
                passed=False,
                score=0.0,
                blocking_reasons=["response_not_evaluated"],
            )])[0],
            provenance=provenance,
            transcript=transcript,
            resolution_stage="closed",
        )
        metrics = context["metrics"]
        successes = [
            label
            for label, value in {
                "evidence_grounded": metrics.evidence_grounding,
                "policy_compliant": metrics.policy_compliance,
                "escalation_routed": metrics.escalation_quality,
                "customer_safe_tone": satisfaction.rubric.get("tone", 0.0),
                "assurance_valid": satisfaction.rubric.get("assurance_validity", 0.0),
            }.items()
            if value >= 0.8
        ]
        failures = [item.failure_type or item.category for item in context.get("diagnosis", [])]
        intelligence = [item.fix or item.rationale for item in context.get("recommendations", [])]
        strategy: ExecutionStrategy = context["execution_strategy"]
        superturiya = SuperTuriyaIntelligence(
            lifecycle=["observe", "trace", "discover", "evaluate", "diagnose", "recommend", "store", "recall", "improve"],
            trace_count=len(spans),
            event_count=len(events),
            events=events,
            discovered_path=[span.agent_name for span in spans],
            successes=successes,
            failures=failures,
            intelligence=intelligence,
            improvement_recommendation_ids=[item.recommendation_id for item in context.get("recommendations", [])],
            recalled_memory_ids=strategy.recalled_intelligence_ids,
            applied_memory_ids=strategy.recalled_intelligence_ids if strategy.memory_influenced_decisions else [],
            created_memory_ids=[
                f"TRAJ-{context['run_id']}",
                f"LTM-{context['run_id']}",
                f"TRANSCRIPT-MEM-{context['run_id']}",
            ],
            feedback_loop_status="closed",
            automatic_policy_mutation=False,
        )
        self._record_operations(context, sarvagun)
        return sarvagun, superturiya

    def persist(self, *, run_id: str, sarvagun: SarvagunExecution, superturiya: SuperTuriyaIntelligence) -> None:
        conversation_id = sarvagun.conversation.conversation_id
        add_short_term_memory(
            conversation_id,
            f"Sarvagun completed {run_id} at stage {sarvagun.resolution_stage}.",
            role="superturiya",
            metadata={"run_id": run_id, "predicted_satisfaction": sarvagun.satisfaction.predicted_satisfaction},
        )
        add_mid_term_summary(
            conversation_id,
            f"{sarvagun.transcript.detected_issue}: {sarvagun.satisfaction.resolution_status}; SuperTuriya stored {len(superturiya.created_memory_ids)} intelligence artifacts.",
            metadata={"run_id": run_id, "customer_id": sarvagun.customer_context.customer_id},
        )
        add_long_term_memory(
            f"TRANSCRIPT-MEM-{run_id}",
            sarvagun.transcript.model_dump_json(),
            metadata={
                "title": f"Redacted Sarvagun transcript intelligence for {run_id}",
                "memory_type": "sarvagun_transcript",
                "run_id": run_id,
                "issue_type": sarvagun.transcript.detected_issue,
                "quality_score": sarvagun.satisfaction.rubric.get("overall_quality"),
                "trust_scope": "superturiya_evaluated_memory",
            },
        )

    def _source_ids(self, context: Dict[str, Any]) -> List[str]:
        return sorted(
            {
                str(card.get("id"))
                for cards in context.get("retrieved_evidence", {}).values()
                for card in cards
                if card.get("id")
            }
        )

    def _provenance(self, context: Dict[str, Any], action: Dict[str, Any]) -> List[ProvenanceRecord]:
        cards = [card for values in context.get("retrieved_evidence", {}).values() for card in values]
        sources = [
            ProvenanceSource(
                source_id=str(card.get("id")),
                title=str(card.get("title", card.get("id"))),
                section=card.get("section"),
                version=str(card.get("version", "demo-v1")),
                category=str(card.get("category", "knowledge")),
            )
            for card in cards
            if card.get("id") in action.get("evidence_ids", [])
        ]
        source_labels = ", ".join(source.source_id for source in sources[:4]) or "governed support evidence"
        tool_labels = ", ".join(tool.tool_name for tool in context["enterprise_tool_executions"])
        return [
            ProvenanceRecord(
                response_id=f"RESP-{context['run_id']}",
                sources=sources,
                tool_executions=context["enterprise_tool_executions"],
                answer_confidence=float(action.get("confidence_score", 0.0)),
                customer_view="Based on the verified case history and the applicable support policy.",
                auditor_view=f"Sources: {source_labels}. Tool executions: {tool_labels}.",
            )
        ]

    def _event(
        self,
        event_type: str,
        conversation_id: str,
        run_id: str,
        actor: str,
        payload: Dict[str, Any],
    ) -> TrajectoryEvent:
        return TrajectoryEvent(
            event_id=f"evt_{uuid4().hex[:12]}",
            event_type=event_type,
            timestamp=_now_iso(),
            conversation_id=conversation_id,
            run_id=run_id,
            correlation_id=observability_context()["correlation_id"],
            actor=actor,
            payload=payload,
        )

    def _append_tool_events(self, context: Dict[str, Any], tool: ToolExecution) -> None:
        conversation_id = context["conversation_signal"].conversation_id
        context["trajectory_events"].extend(
            [
                self._event(
                    "tool.called",
                    conversation_id,
                    context["run_id"],
                    tool.tool_name,
                    {
                        "tool_execution_id": tool.tool_execution_id,
                        "operation": tool.operation,
                        "access_type": tool.access_type,
                        "authorization": tool.authorization,
                        "idempotency_key": tool.idempotency_key,
                    },
                ),
                self._event("tool.completed", conversation_id, context["run_id"], tool.tool_name, tool.model_dump()),
            ]
        )

    def _record_operations(self, context: Dict[str, Any], sarvagun: SarvagunExecution) -> None:
        with _OPERATIONS_LOCK:
            _OPERATIONS.append(
                {
                    "run_id": context["run_id"],
                    "conversation_id": sarvagun.conversation.conversation_id,
                    "customer_id": sarvagun.customer_context.customer_id,
                    "customer_name": sarvagun.customer_context.customer_name,
                    "issue": sarvagun.transcript.detected_issue,
                    "emotion": sarvagun.emotion.primary_emotion,
                    "stage": sarvagun.resolution_stage,
                    "recontact": sarvagun.recontact.recontact_detected,
                    "escalation": sarvagun.escalation.status,
                    "incident": sarvagun.incident.incident_id,
                    "predicted_satisfaction": sarvagun.satisfaction.predicted_satisfaction,
                    "created_at": _now_iso(),
                }
            )
            del _OPERATIONS[:-100]


def operations_snapshot() -> Dict[str, Any]:
    with _OPERATIONS_LOCK:
        rows = list(_OPERATIONS)
    return {
        "system": "Sarvagun",
        "intelligence": "SuperTuriya",
        "active_conversations": 0,
        "waiting_for_response": 0,
        "resolved_or_escalated_today": len(rows),
        "escalations_open": sum(1 for row in rows if row["escalation"] in {"ESCALATED", "APPROVAL_REQUIRED"}),
        "predicted_dissatisfaction": sum(1 for row in rows if row["predicted_satisfaction"] < 0.5),
        "recontact_rate": round(sum(1 for row in rows if row["recontact"]) / max(1, len(rows)), 3),
        "active_incidents": len({row["incident"] for row in rows if row["incident"]}),
        "conversations": rows[-20:],
    }


def store_explicit_feedback(run_id: str, explicit_csat: int, explicit_resolution: str) -> Dict[str, Any]:
    record = {
        "run_id": run_id,
        "explicit_csat": explicit_csat,
        "explicit_resolution": explicit_resolution,
        "recorded_at": _now_iso(),
        "metric_type": "explicit_customer_feedback",
    }
    _EXPLICIT_FEEDBACK[run_id] = record
    add_short_term_memory(run_id, str(record), role="explicit_customer_feedback")
    return record


sarvagun_lifecycle = SarvagunLifecycle()
