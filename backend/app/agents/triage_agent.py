from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class TriageAgent:
    name = "Intake / Triage Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        classifications: Dict[str, Dict[str, Any]] = {}
        risk_flags: List[str] = []

        for ticket in context["tickets"]:
            ticket_flags: List[str] = []
            message = str(context.get("customer_query") or ticket.message).lower()
            sla_risk = "low"
            if ticket.priority == "critical":
                sla_risk = "critical"
                ticket_flags.append("SLA_BREACH_RISK")
            elif ticket.priority == "high" or ticket.plan == "enterprise":
                sla_risk = "high"
                ticket_flags.append("SLA_REVIEW_REQUIRED")

            if ticket.sentiment in {"angry", "urgent", "frustrated"}:
                ticket_flags.append("CUSTOMER_SENTIMENT_RISK")
            if "cancel" in message or "move providers" in message:
                ticket_flags.append("CHURN_RISK")
            if ticket.issue_type == "security_data_deletion":
                ticket_flags.append("SECURITY_SENSITIVE")
            if ticket.issue_type == "billing_refund":
                ticket_flags.append("BILLING_APPROVAL_RISK")

            classifications[ticket.ticket_id] = {
                "ticket_id": ticket.ticket_id,
                "issue_type": ticket.issue_type,
                "urgency": ticket.priority,
                "customer_tier": ticket.plan,
                "sla_risk": sla_risk,
                "sentiment": ticket.sentiment,
                "risk_flags": ticket_flags,
            }
            risk_flags.extend(ticket_flags)

        context["triage"] = classifications
        return {
            "summary": f"Classified {len(classifications)} support tickets and identified {len(set(risk_flags))} distinct risk flags.",
            "classifications": classifications,
            "tools_used": ["priority_rules", "sentiment_rules", "sla_window_rules"],
            "evidence_ids": [],
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.9,
        }
