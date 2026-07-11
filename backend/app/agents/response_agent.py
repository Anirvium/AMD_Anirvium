from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.schemas.run import FinalAction
from app.schemas.trajectory import ApprovalState
from app.services.model_router import ModelRole


logger = logging.getLogger("uvicorn.error")


class ResponseDraftingAgent:
    name = "Response Drafting Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        final_actions: List[Dict[str, Any]] = []
        evidence_ids: List[str] = []
        risk_flags: List[str] = []
        model_router = context.get("model_router")
        llm_client = context.get("llm_client")
        model_name = (
            model_router.route(ModelRole.TEXT_AGENT).model_name
            if model_router
            else "Qwen/Qwen3-14B"
        )
        llm_used = False

        for ticket in context["tickets"]:
            escalation = context["escalations"][ticket.ticket_id]
            policy = context["policy_checks"][ticket.ticket_id]
            ticket_evidence = escalation["evidence_ids"]
            approval_state = policy["approval_state"]
            draft = self._draft_response(ticket, escalation, approval_state, ticket_evidence)
            llm_draft = self._draft_with_llm(
                llm_client=llm_client,
                ticket=ticket,
                escalation=escalation,
                policy=policy,
                customer_query=context.get("customer_query"),
                fallback=draft,
            )
            if llm_draft != draft:
                draft = llm_draft
                llm_used = True

            action = FinalAction(
                ticket_id=ticket.ticket_id,
                customer_name=ticket.customer_name,
                recommended_escalation=escalation["recommended_escalation"],
                owner=escalation["owner"],
                urgency=escalation["urgency"],
                approval_state=approval_state,
                draft_response=draft,
                evidence_ids=ticket_evidence,
                risk_flags=policy["risk_flags"],
                next_action=escalation["next_action"],
            ).model_dump()
            final_actions.append(action)
            evidence_ids.extend(ticket_evidence)
            risk_flags.extend(policy["risk_flags"])

        context["final_actions"] = final_actions
        return {
            "summary": f"Drafted {len(final_actions)} customer-safe responses with approval states and evidence IDs.",
            "final_actions": final_actions,
            "tools_used": ["safe_response_template", "approval_gate_check"] + (["llm_response_drafting"] if llm_used else []),
            "evidence_ids": sorted(set(evidence_ids)),
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.APPROVAL_REQUIRED.value if risk_flags else ApprovalState.DRAFT_RECOMMENDATION.value,
            "model_name": model_name,
            "confidence": 0.86,
        }

    def _draft_response(
        self,
        ticket: Any,
        escalation: Dict[str, Any],
        approval_state: str,
        evidence_ids: List[str],
    ) -> str:
        evidence_text = ", ".join(evidence_ids)
        approval_note = ""
        if approval_state == ApprovalState.APPROVAL_REQUIRED.value:
            approval_note = " Any refund, security, compensation, or contractual commitment will remain pending until the required approval is complete."

        curated_note = ""
        if any(evidence_id.startswith(("POL-CS-", "PROC-CS-", "TMPL-CS-")) for evidence_id in evidence_ids):
            curated_note = " I will keep this aligned with the verified support policy and only confirm outcomes after the responsible team has evidence."

        if ticket.issue_type == "production_outage":
            body = (
                f"Hi {ticket.customer_name} team, we understand the urgency of the production outage and the SLA risk. "
                f"We are routing this to {escalation['recommended_escalation']} with {escalation['owner']} assigned. "
                "The next action is to verify the affected region, impact scope, and incident timeline before sending the next update."
            )
        elif ticket.issue_type == "billing_refund":
            body = (
                f"Hi {ticket.customer_name} team, we understand the urgency around the duplicate annual charge. "
                f"We are assigning this to {escalation['owner']} to verify the invoice and prepare a billing review. "
                "We can acknowledge the dispute now, but we cannot confirm a refund or credit until billing approval is recorded."
            )
        elif ticket.issue_type == "security_data_deletion":
            body = (
                f"Hi {ticket.customer_name} team, we understand this is time-sensitive for your audit process. "
                f"We are routing the request to {escalation['recommended_escalation']} so identity and account authority can be verified. "
                "We cannot confirm deletion or access changes until security review is complete."
            )
        elif ticket.issue_type == "integration_failure":
            body = (
                f"Hi {ticket.customer_name} team, we understand the integration blocker is affecting your reporting deadline. "
                f"We are routing this to {escalation['recommended_escalation']} with {escalation['owner']} assigned. "
                "The next action is to inspect connector authentication changes, error payloads, and sync retry state."
            )
        elif ticket.issue_type == "churn_risk":
            body = (
                f"Hi {ticket.customer_name} team, we understand the repeated automation failures are creating real frustration. "
                f"We are assigning {escalation['owner']} to coordinate recovery outreach and collect a root-cause summary. "
                "The next action is to consolidate the recent failures and identify the fastest stabilizing fix."
            )
        elif ticket.issue_type == "feature_request":
            body = (
                f"Hi {ticket.customer_name} team, thanks for sharing the SAML group-mapping expansion need. "
                f"We are routing this to {escalation['recommended_escalation']} so roadmap status and expansion impact can be reviewed. "
                "The next action is to confirm current product guidance with Customer Success."
            )
        elif ticket.issue_type == "duplicate_low_priority":
            body = (
                f"Hi {ticket.customer_name} team, we found this appears to duplicate an existing notification-settings request. "
                "We are merging the duplicate and keeping the active thread open so the support queue has one source of truth."
            )
        elif ticket.issue_type == "deposit_missing":
            body = (
                f"Hi {ticket.customer_name}, I understand you are waiting for your deposit to appear. "
                f"We are routing this to {escalation['owner']} to check the payment window and proof. "
                "If the normal processing window has passed, we will use the successful payment evidence to continue the financial review."
            )
        elif ticket.issue_type == "withdrawal_processed_missing":
            body = (
                f"Hi {ticket.customer_name}, I understand the concern. "
                f"We are assigning this to {escalation['owner']} to verify the processed date and tracking evidence. "
                "If the bank cannot locate the funds, the next step is to attach the bank statement or official bank response for financial review."
            )
        elif ticket.issue_type == "verification_restriction":
            body = (
                f"Hi {ticket.customer_name}, your account restriction needs to remain tied to the verification review. "
                f"We are routing this to {escalation['owner']} to confirm the missing documents and review status. "
                "We cannot confirm restriction removal until the responsible team completes verification."
            )
        elif ticket.issue_type == "bonus_dispute":
            body = (
                f"Hi {ticket.customer_name}, I understand you want the bonus restored or a new promo code. "
                f"We are assigning this to {escalation['owner']} to check active bonus status and available offers. "
                "We can explain the available options after checking account-specific bonus evidence."
            )
        elif ticket.issue_type == "cross_account_access":
            body = (
                f"Hi {ticket.customer_name}, for security reasons we can only share account-specific details through a verified contact channel. "
                f"We are routing this to {escalation['owner']} so ownership can be verified before any balance or account status is discussed."
            )
        elif ticket.issue_type == "priority_policy_exception":
            body = (
                f"Hi {ticket.customer_name}, I understand this is urgent and we are escalating ownership through {escalation['owner']}. "
                "Priority handling can speed up review, but verification and withdrawal controls still need to be completed before any release or exception is confirmed."
            )
        else:
            body = (
                f"Hi {ticket.customer_name} team, thanks for the detail. "
                f"We are routing this to {escalation['recommended_escalation']} and tracking the next action: {escalation['next_action']}."
            )

        return f"{body}{approval_note}{curated_note} Internal evidence: {evidence_text}."

    def _draft_with_llm(
        self,
        *,
        llm_client: Any,
        ticket: Any,
        escalation: Dict[str, Any],
        policy: Dict[str, Any],
        fallback: str,
        customer_query: str | None = None,
    ) -> str:
        if llm_client is None or getattr(llm_client, "model_name", "mock-trajectory-model") == "mock-trajectory-model":
            return fallback
        prompt = (
            "Draft one concise customer-safe support response. "
            "Never promise refunds, account unblocking, withdrawal completion, security actions, compensation, or policy exceptions. "
            "Respect the approval state and constraints. Do not expose internal-only reasoning. "
            f"Customer request: {customer_query or ticket.message}\n"
            f"Matched support case: {getattr(ticket, 'issue_type', 'customer_support')}\n"
            f"Customer: {ticket.customer_name}\n"
            f"Escalation: {escalation}\n"
            f"Policy: {policy}\n"
            f"Fallback safe draft to improve without weakening safety: {fallback}"
        )
        try:
            response = llm_client.generate(
                [
                    {"role": "system", "content": "You are a policy-safe enterprise support response drafting agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
        except Exception:
            logger.exception("response_drafting_llm_fallback ticket_id=%s reason=call_failed", getattr(ticket, "ticket_id", "unknown"))
            return fallback
        text = response.text.strip()
        if not text:
            logger.warning("response_drafting_llm_fallback ticket_id=%s reason=empty_public_output", getattr(ticket, "ticket_id", "unknown"))
            return fallback
        if any(term in text.lower() for term in ("guaranteed", "will refund", "will unblock", "skip verification")):
            logger.warning("response_drafting_llm_fallback ticket_id=%s reason=unsafe_output", getattr(ticket, "ticket_id", "unknown"))
            return fallback
        return text
