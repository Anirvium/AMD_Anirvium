from __future__ import annotations

from typing import Any, Dict, List, Set

from app.schemas.evaluation import DiagnosisItem, EvaluationMetrics
from app.schemas.ticket import SupportTicket
from app.schemas.trajectory import TrajectorySpan


class FailureDiagnosisEngine:
    def diagnose(
        self,
        context: Dict[str, Any],
        metrics: EvaluationMetrics,
        spans: List[TrajectorySpan],
    ) -> List[DiagnosisItem]:
        tickets: List[SupportTicket] = context["tickets"]
        final_actions: List[Dict[str, Any]] = context.get("final_actions", [])
        action_by_ticket = {action["ticket_id"]: action for action in final_actions}
        diagnosis: List[DiagnosisItem] = []

        for ticket in tickets:
            action = action_by_ticket.get(ticket.ticket_id)
            if not action:
                diagnosis.append(
                    self._item(
                        category="missing_information",
                        failure_type="MISSING_FINAL_ACTION",
                        severity="HIGH",
                        ticket_id=ticket.ticket_id,
                        affected_agent="Response Drafting Agent",
                        message="No final action was produced for the ticket.",
                        evidence_ids=[ticket.ticket_id],
                        business_impact="Support managers cannot approve or act on a ticket that has no final recommendation.",
                        recommended_fix="Require the response drafter to emit one final action per selected ticket.",
                        metric_impact=["task_completion", "actionability"],
                        confidence=0.96,
                    )
                )
                continue

            expected: Set[str] = set(ticket.expected_evidence_ids)
            used: Set[str] = set(action.get("evidence_ids", []))
            missing = sorted(expected - used)
            if missing:
                diagnosis.append(
                    self._item(
                        category="missing_evidence",
                        failure_type="MISSING_EXPECTED_EVIDENCE",
                        severity="MEDIUM",
                        ticket_id=ticket.ticket_id,
                        affected_agent="Knowledge Retrieval Agent",
                        message=f"Final action is missing expected evidence IDs: {', '.join(missing)}.",
                        evidence_ids=missing,
                        business_impact="A support manager may not be able to verify whether the recommendation is grounded in policy or KB evidence.",
                        recommended_fix="Add a mandatory evidence checklist before drafting the final response.",
                        metric_impact=["evidence_grounding", "hallucination_risk"],
                        confidence=0.9,
                    )
                )

            draft = action.get("draft_response", "").lower()
            if action.get("urgency") in {"critical", "high"} and not self._has_update_cadence(draft):
                diagnosis.append(
                    self._item(
                        category="weak_response",
                        failure_type="MISSING_CUSTOMER_UPDATE_CADENCE",
                        severity="MEDIUM",
                        ticket_id=ticket.ticket_id,
                        affected_agent="Response Drafting Agent",
                        message="High-urgency response does not state a customer update cadence.",
                        evidence_ids=action.get("evidence_ids", []),
                        business_impact="Urgent customers may remain uncertain about ownership and timing, increasing churn or SLA pressure.",
                        recommended_fix="Require a next-update field for critical and high-priority customer replies.",
                        metric_impact=["missing_information", "customer_tone", "actionability"],
                        confidence=0.88,
                    )
                )

            if ticket.issue_type in {"billing_refund", "security_data_deletion"} and action.get("approval_state") != "APPROVAL_REQUIRED":
                diagnosis.append(
                    self._item(
                        category="policy_violation",
                        failure_type="SENSITIVE_ACTION_WITHOUT_APPROVAL",
                        severity="CRITICAL",
                        ticket_id=ticket.ticket_id,
                        affected_agent="Policy Checker Agent",
                        message="Sensitive action was not held for approval.",
                        evidence_ids=action.get("evidence_ids", []),
                        business_impact="The company could make an unauthorized refund, security, deletion, or compliance commitment.",
                        recommended_fix="Gate refund, data deletion, and security actions behind approval workflow.",
                        metric_impact=["policy_compliance", "hallucination_risk"],
                        confidence=0.95,
                    )
                )

            if "will refund" in draft or "will delete" in draft:
                diagnosis.append(
                    self._item(
                        category="unsafe_action_without_approval",
                        failure_type="UNSAFE_CUSTOMER_COMMITMENT",
                        severity="CRITICAL",
                        ticket_id=ticket.ticket_id,
                        affected_agent="Response Drafting Agent",
                        message="Draft response appears to commit to a sensitive action.",
                        evidence_ids=action.get("evidence_ids", []),
                        business_impact="A customer-facing message could promise a restricted action before the required human approval exists.",
                        recommended_fix="Rewrite the response as a draft recommendation pending approval.",
                        metric_impact=["policy_compliance", "customer_tone"],
                        confidence=0.93,
                    )
                )

        total_tokens = sum(span.tokens_in + span.tokens_out for span in spans)
        if total_tokens > 4200:
            diagnosis.append(
                self._item(
                    category="excessive_token_usage",
                    failure_type="EXCESSIVE_TOKEN_USAGE",
                    severity="LOW",
                    affected_agent="Knowledge Retrieval Agent",
                    message=f"Run used {total_tokens} estimated tokens.",
                    business_impact="Large queues become more expensive and slower to evaluate at scale.",
                    recommended_fix="Compress retrieved evidence summaries and avoid repeating full policy text in later steps.",
                    metric_impact=["token_efficiency", "latency_efficiency"],
                    confidence=0.82,
                )
            )

        low_confidence_steps = [span for span in spans if span.confidence < 0.72]
        for span in low_confidence_steps:
            diagnosis.append(
                self._item(
                    category="low_confidence",
                    failure_type="LOW_CONFIDENCE_AGENT_STEP",
                    severity="MEDIUM",
                    affected_agent=span.agent_name,
                    message=f"{span.agent_name} confidence is {span.confidence:.2f}.",
                    evidence_ids=span.evidence_ids,
                    business_impact="Low-confidence intermediate reasoning can propagate into unsafe or vague final recommendations.",
                    recommended_fix="Route low-confidence spans to a critic pass before final customer drafting.",
                    metric_impact=["task_completion", "actionability"],
                    confidence=0.84,
                )
            )

        if not diagnosis:
            diagnosis.append(
                self._item(
                    category="residual_risk",
                    failure_type="RESIDUAL_APPROVAL_RISK",
                    severity="LOW",
                    affected_agent="Policy Checker Agent",
                    message="No blocking failures found; keep approval gates and evidence checks in place.",
                    business_impact="Human approval outcomes are still needed to calibrate future automation thresholds.",
                    recommended_fix="Record human approval outcome after sensitive recommendations are reviewed.",
                    metric_impact=["policy_compliance"],
                    confidence=0.78,
                )
            )

        return diagnosis

    def _has_update_cadence(self, draft: str) -> bool:
        cadence_terms = ["next update at", "within", "minutes", "hour", " by "]
        return "next update" in draft and any(term in draft for term in cadence_terms)

    def _item(
        self,
        *,
        category: str,
        failure_type: str,
        severity: str,
        message: str,
        business_impact: str,
        recommended_fix: str,
        affected_agent: str,
        metric_impact: List[str],
        confidence: float,
        ticket_id: str | None = None,
        evidence_ids: List[str] | None = None,
    ) -> DiagnosisItem:
        return DiagnosisItem(
            category=category,
            failure_type=failure_type,
            severity=severity,
            ticket_id=ticket_id,
            affected_agent=affected_agent,
            message=message,
            evidence_ids=evidence_ids or [],
            business_impact=business_impact,
            suggested_fix=recommended_fix,
            recommended_fix=recommended_fix,
            metric_impact=metric_impact,
            confidence=confidence,
        )
