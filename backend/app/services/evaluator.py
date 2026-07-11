from __future__ import annotations

from typing import Any, Dict, List, Set

from app.schemas.evaluation import EvaluationMetrics
from app.schemas.ticket import SupportTicket
from app.schemas.trajectory import TrajectorySpan


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def _has_update_cadence(draft: str) -> bool:
    cadence_terms = ["next update at", "within", "minutes", "hour", " by "]
    return "next update" in draft and any(term in draft for term in cadence_terms)


class EvaluationEngine:
    def score(self, context: Dict[str, Any], spans: List[TrajectorySpan]) -> EvaluationMetrics:
        tickets: List[SupportTicket] = context["tickets"]
        final_actions: List[Dict[str, Any]] = context.get("final_actions", [])
        action_by_ticket = {action["ticket_id"]: action for action in final_actions}

        expected_evidence: Set[str] = set()
        for ticket in tickets:
            expected_evidence.update(ticket.expected_evidence_ids)
        used_evidence = set()
        for action in final_actions:
            used_evidence.update(action.get("evidence_ids", []))
        evidence_grounding = _clamp(len(used_evidence & expected_evidence) / max(1, len(expected_evidence)))
        visual_evidence_ids = {
            item.get("evidence_id")
            for item in context.get("visual_evidence_cards", [])
            if item.get("evidence_id")
        }
        visual_grounding = _clamp(len(used_evidence & visual_evidence_ids) / max(1, len(visual_evidence_ids))) if visual_evidence_ids else 1.0

        sensitive_tickets = [
            ticket
            for ticket in tickets
            if ticket.issue_type in {"billing_refund", "deposit_missing", "withdrawal_processed_missing", "bonus_dispute", "security_data_deletion"}
            or ticket.issue_type in {"verification_restriction", "cross_account_access", "priority_policy_exception"}
            or (ticket.plan == "enterprise" and ticket.priority in {"high", "critical"})
        ]
        if not sensitive_tickets:
            policy_compliance = 1.0
        else:
            compliant_sensitive = 0
            for ticket in sensitive_tickets:
                action = action_by_ticket.get(ticket.ticket_id, {})
                if action.get("approval_state") in {"APPROVAL_REQUIRED", "ESCALATED"}:
                    compliant_sensitive += 1
            policy_compliance = _clamp(compliant_sensitive / len(sensitive_tickets))

        expected_escalations = [
            ticket
            for ticket in tickets
            if ticket.priority in {"high", "critical"} or ticket.plan == "enterprise"
        ]
        correct_escalations = 0
        for ticket in expected_escalations:
            action = action_by_ticket.get(ticket.ticket_id, {})
            route = action.get("recommended_escalation", "").lower()
            if ticket.issue_type == "billing_refund" and "billing" in route:
                correct_escalations += 1
            elif ticket.issue_type == "security_data_deletion" and "security" in route:
                correct_escalations += 1
            elif ticket.issue_type in {"production_outage", "integration_failure"} and "engineering" in route:
                correct_escalations += 1
            elif ticket.issue_type in {"churn_risk", "feature_request"} and "customer success" in route:
                correct_escalations += 1
            elif ticket.issue_type in {"deposit_missing", "withdrawal_processed_missing"} and "financial" in route:
                correct_escalations += 1
            elif ticket.issue_type == "verification_restriction" and "verification" in route:
                correct_escalations += 1
            elif ticket.issue_type == "cross_account_access" and "security" in route:
                correct_escalations += 1
            elif ticket.issue_type == "priority_policy_exception" and "priority" in route:
                correct_escalations += 1
        escalation_quality = _clamp(correct_escalations / max(1, len(expected_escalations)))

        completed_actions = len(final_actions) / max(1, len(tickets))
        task_completion = _clamp(completed_actions)

        unsafe_terms = {"guarantee", "guaranteed", "will refund", "will delete", "legal commitment"}
        unsafe_mentions = 0
        tone_hits = 0
        actionability_hits = 0
        missing_info = 0
        for action in final_actions:
            draft = action.get("draft_response", "").lower()
            if any(term in draft for term in unsafe_terms):
                unsafe_mentions += 1
            if "urgency" in action and "next_action" in action and action.get("owner"):
                actionability_hits += 1
            if any(
                term in draft
                for term in [
                    "understand",
                    "sorry",
                    "frustrating",
                    "checked the case history",
                    "we are routing",
                    "we are assigning",
                ]
            ):
                tone_hits += 1
            if not _has_update_cadence(draft) and action.get("urgency") in {"critical", "high"}:
                missing_info += 1

        hallucination_risk = _clamp(0.08 + 0.14 * unsafe_mentions)
        actionability = _clamp(actionability_hits / max(1, len(final_actions)))
        customer_tone = _clamp(tone_hits / max(1, len(final_actions)))
        missing_information = _clamp(missing_info / max(1, len(final_actions)))

        total_tokens = sum(span.tokens_in + span.tokens_out for span in spans)
        token_efficiency = _clamp(1.0 - max(0, total_tokens - 3200) / 9000)
        total_latency = sum(span.latency_ms for span in spans)
        latency_efficiency = _clamp(1.0 - max(0, total_latency - 1200) / 5000)

        positive_average = (
            task_completion
            + evidence_grounding
            + visual_grounding
            + policy_compliance
            + escalation_quality
            + actionability
            + customer_tone
            + token_efficiency
            + latency_efficiency
            + (1.0 - hallucination_risk)
            + (1.0 - missing_information)
        ) / 11
        overall_score = round(positive_average * 100, 1)

        return EvaluationMetrics(
            task_completion=task_completion,
            evidence_grounding=evidence_grounding,
            policy_compliance=policy_compliance,
            hallucination_risk=hallucination_risk,
            escalation_quality=escalation_quality,
            actionability=actionability,
            missing_information=missing_information,
            customer_tone=customer_tone,
            token_efficiency=token_efficiency,
            latency_efficiency=latency_efficiency,
            overall_score=overall_score,
        )
