from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class PolicyCheckerAgent:
    name = "Policy Checker Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        policy_checks: Dict[str, Dict[str, Any]] = {}
        evidence_ids: List[str] = []
        risk_flags: List[str] = []

        for ticket in context["tickets"]:
            ticket_evidence = [card["id"] for card in context["retrieved_evidence"][ticket.ticket_id]]
            ticket_flags: List[str] = []
            approval_state = ApprovalState.DRAFT_RECOMMENDATION.value
            constraints: List[str] = []
            retrieved_cards = context["retrieved_evidence"][ticket.ticket_id]

            if ticket.issue_type == "billing_refund":
                approval_state = ApprovalState.APPROVAL_REQUIRED.value
                ticket_flags.append("REFUND_APPROVAL_REQUIRED")
                constraints.append("Do not promise refund, credit, or reversal before billing approval.")

            if ticket.issue_type == "security_data_deletion":
                approval_state = ApprovalState.APPROVAL_REQUIRED.value
                ticket_flags.append("SECURITY_APPROVAL_REQUIRED")
                constraints.append("Verify identity and route to security before confirming deletion or access changes.")

            if ticket.issue_type in {"verification_restriction", "cross_account_access", "priority_policy_exception"}:
                approval_state = ApprovalState.APPROVAL_REQUIRED.value
                ticket_flags.append("CUSTOMER_SUPPORT_APPROVAL_REQUIRED")
                constraints.append("Do not bypass verification, account ownership, or payment controls without responsible-team approval.")

            if ticket.plan == "enterprise" and ticket.priority in {"high", "critical"}:
                if approval_state == ApprovalState.DRAFT_RECOMMENDATION.value:
                    approval_state = ApprovalState.APPROVAL_REQUIRED.value
                ticket_flags.append("ENTERPRISE_SLA_ESCALATION_REQUIRED")
                constraints.append("Assign an owner and escalate before SLA risk increases.")

            for card in retrieved_cards:
                if not str(card.get("id", "")).startswith("POL-CS-"):
                    continue
                if card.get("requires_approval"):
                    approval_state = ApprovalState.APPROVAL_REQUIRED.value
                    ticket_flags.append(f"{card['id']}_APPROVAL_REQUIRED")
                constraints.append(f"Apply {card['id']}: {card['summary']}")

            constraints.append("Cite internal evidence IDs for material recommendations.")

            policy_checks[ticket.ticket_id] = {
                "ticket_id": ticket.ticket_id,
                "approval_state": approval_state,
                "constraints": constraints,
                "risk_flags": ticket_flags,
                "evidence_ids": ticket_evidence,
            }
            evidence_ids.extend(ticket_evidence)
            risk_flags.extend(ticket_flags)

        context["policy_checks"] = policy_checks
        return {
            "summary": f"Applied policy gates to {len(policy_checks)} tickets; {len(set(risk_flags))} sensitive conditions found.",
            "policy_checks": policy_checks,
            "tools_used": ["policy_rules_engine", "approval_state_classifier"],
            "evidence_ids": sorted(set(evidence_ids)),
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.APPROVAL_REQUIRED.value if risk_flags else ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.91,
        }
