from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class EscalationAgent:
    name = "Escalation Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        customers = context["customers_by_id"]
        escalations: Dict[str, Dict[str, Any]] = {}
        evidence_ids: List[str] = []
        risk_flags: List[str] = []

        for ticket in context["tickets"]:
            customer = customers.get(ticket.customer_id, {})
            success_owner = customer.get("success_owner", "Customer Success queue")
            route = "Support operations"
            owner = "Support queue"
            urgency = ticket.priority
            next_action = "Continue standard support triage."

            if ticket.issue_type == "production_outage":
                route = "Engineering incident response + Customer Success"
                owner = f"Engineering Incident Commander with {success_owner}"
                next_action = "Open incident bridge, verify affected region, and send executive-safe customer update."
            elif ticket.issue_type == "billing_refund":
                route = "Billing operations"
                owner = "Billing approval queue"
                next_action = "Verify invoice and prepare refund recommendation for billing approval."
            elif ticket.issue_type == "security_data_deletion":
                route = "Security operations"
                owner = "Security operations lead"
                next_action = "Verify requester authority and begin data deletion workflow review."
            elif ticket.issue_type == "churn_risk":
                route = "Customer Success"
                owner = success_owner
                next_action = "Schedule recovery outreach and collect root-cause summary."
            elif ticket.issue_type == "integration_failure":
                route = "Engineering integrations + Customer Success"
                owner = f"Integration support engineer with {success_owner}"
                next_action = "Inspect connector auth changes and restore sync before reporting deadline."
            elif ticket.issue_type == "feature_request":
                route = "Product management + Customer Success"
                owner = success_owner
                next_action = "Confirm roadmap status and collect expansion impact."
            elif ticket.issue_type == "duplicate_low_priority":
                route = "Support operations"
                owner = "Support queue"
                next_action = "Merge duplicate ticket and point customer to account notification settings."
            elif ticket.issue_type == "deposit_missing":
                route = "Financial operations"
                owner = "Deposit review queue"
                next_action = "Check elapsed payment window, request proof if needed, and create or update the financial task."
            elif ticket.issue_type == "withdrawal_processed_missing":
                route = "Financial operations"
                owner = "Withdrawal review queue"
                next_action = "Verify processed date, request bank proof or official response, and escalate tracking evidence."
            elif ticket.issue_type == "verification_restriction":
                route = "Verification team"
                owner = "Verification review queue"
                next_action = "Confirm missing documents and keep restriction removal pending until verification review completes."
            elif ticket.issue_type == "bonus_dispute":
                route = "Support operations"
                owner = "Bonus support queue"
                next_action = "Check active bonus state and promo-code availability before explaining options."
            elif ticket.issue_type == "cross_account_access":
                route = "Account security"
                owner = "Account security queue"
                next_action = "Require registered-channel contact or identity verification before sharing account-specific details."
            elif ticket.issue_type == "priority_policy_exception":
                route = "Priority support + Verification team"
                owner = "Priority support queue"
                next_action = "Escalate ownership while keeping verification and withdrawal policy gates active."

            ticket_evidence = [card["id"] for card in context["retrieved_evidence"][ticket.ticket_id]]
            if urgency in {"critical", "high"}:
                risk_flags.append("ESCALATION_TIME_SENSITIVE")

            escalations[ticket.ticket_id] = {
                "ticket_id": ticket.ticket_id,
                "recommended_escalation": route,
                "owner": owner,
                "urgency": urgency,
                "next_action": next_action,
                "evidence_ids": ticket_evidence,
            }
            evidence_ids.extend(ticket_evidence)

        context["escalations"] = escalations
        return {
            "summary": f"Produced escalation routes and owners for {len(escalations)} tickets.",
            "escalations": escalations,
            "tools_used": ["escalation_matrix", "customer_success_owner_lookup"],
            "evidence_ids": sorted(set(evidence_ids)),
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.ESCALATED.value if risk_flags else ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.88,
        }
