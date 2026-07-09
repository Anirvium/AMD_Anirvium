from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class PlannerAgent:
    name = "Planner Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        plans: Dict[str, Dict[str, Any]] = {}
        risk_flags: List[str] = []

        for ticket in context["tickets"]:
            issue_type = ticket.issue_type
            stop_conditions = self._stop_conditions(issue_type)
            required_evidence = self._required_evidence(issue_type)
            plan = {
                "ticket_id": ticket.ticket_id,
                "intent": issue_type,
                "case_risk": self._case_risk(ticket),
                "plan_steps": [
                    "classify customer intent, sentiment, priority, and SLA pressure",
                    "retrieve support policy, procedure, template, and evidence records",
                    "apply plan-driven policy gates before drafting",
                    "draft a customer-safe response grounded in evidence IDs",
                    "run compliance and confidence gates before final action",
                    "handoff to a human when confidence, approval, or policy state requires it",
                    "feed completed trajectory into reflection, learning extraction, and optimizer loops",
                ],
                "required_tools": ["triage_classifier", "kb_search", "policy_check", "evidence_card_lookup"],
                "required_evidence": required_evidence,
                "stop_conditions": stop_conditions,
                "policy_mode": "hybrid_plan_driven_and_ai_driven",
                "reasoning_summary": (
                    f"Plan for {ticket.ticket_id}: handle {issue_type} by retrieving evidence first, "
                    "then enforcing policy gates before any customer-facing commitment."
                ),
            }
            plans[ticket.ticket_id] = plan
            if stop_conditions:
                risk_flags.extend([f"PLAN_STOP_{item.upper()}" for item in stop_conditions])

        context["plans"] = plans
        return {
            "summary": f"Created plan-driven support workflow for {len(plans)} selected tickets.",
            "plans": plans,
            "tools_used": ["plan_policy_router", "risk_stop_condition_builder", "workflow_contract_generator"],
            "evidence_ids": [],
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "reasoning_summary": "Planner produced auditable reasoning summaries, required evidence, tool sequence, and stop conditions without exposing private reasoning.",
            "confidence": 0.9,
        }

    def _case_risk(self, ticket: Any) -> str:
        if ticket.priority == "critical":
            return "critical_customer_or_financial_risk"
        if ticket.priority == "high" or ticket.plan == "enterprise":
            return "high_support_risk"
        return "standard_support_risk"

    def _required_evidence(self, issue_type: str) -> List[str]:
        if issue_type in {"deposit_missing", "withdrawal_processed_missing", "billing_refund"}:
            return ["payment status", "transaction proof", "financial policy"]
        if issue_type in {"verification_restriction", "cross_account_access", "security_data_deletion"}:
            return ["identity authority", "account security policy", "verification status"]
        if issue_type in {"bonus_dispute", "priority_policy_exception"}:
            return ["bonus policy", "account eligibility", "approval policy"]
        return ["ticket history", "support policy", "customer-facing template"]

    def _stop_conditions(self, issue_type: str) -> List[str]:
        conditions = ["unsupported_commitment_without_evidence"]
        if issue_type in {"deposit_missing", "withdrawal_processed_missing", "billing_refund"}:
            conditions.extend(["refund_or_release_promise", "financial_outcome_without_approval"])
        if issue_type in {"verification_restriction", "cross_account_access", "security_data_deletion"}:
            conditions.extend(["verification_bypass", "account_detail_disclosure"])
        if issue_type in {"bonus_dispute", "priority_policy_exception"}:
            conditions.append("policy_exception_without_approval")
        return conditions
