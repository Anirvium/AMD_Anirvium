from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class ComplianceAgent:
    name = "Compliance Agent"

    prohibited_commitments = {
        "will refund": "refund_commitment",
        "will compensate": "compensation_commitment",
        "will unblock": "account_unblock_commitment",
        "skip verification": "verification_bypass",
        "guaranteed": "unsupported_guarantee",
        "legal commitment": "legal_commitment",
    }

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        compliance_checks: Dict[str, Dict[str, Any]] = {}
        evidence_ids: List[str] = []
        risk_flags: List[str] = []
        material_risk_flags: List[str] = []

        for action in context.get("final_actions", []):
            status = "PASS"
            violations: List[str] = []
            remediations: List[str] = []
            required_evidence = action.get("evidence_ids", [])
            draft = action.get("draft_response", "")
            lower_draft = draft.lower()

            for phrase, violation in self.prohibited_commitments.items():
                if phrase in lower_draft:
                    violations.append(violation)

            if "internal evidence:" in lower_draft:
                remediations.append("internal_evidence_disclosure_rewritten")
                action["draft_response"] = self._remove_internal_evidence(draft)

            if not required_evidence:
                violations.append("missing_structured_evidence")

            if action.get("approval_state") == ApprovalState.APPROVAL_REQUIRED.value:
                violations.append("approval_required_before_send")

            if any(item in violations for item in {"refund_commitment", "compensation_commitment", "account_unblock_commitment", "verification_bypass", "legal_commitment"}):
                status = "BLOCKED"
            elif violations:
                status = "REVIEW_REQUIRED"

            action["compliance_status"] = status
            material_flags = [f"COMPLIANCE_{item.upper()}" for item in violations]
            remediation_flags = [f"COMPLIANCE_{item.upper()}" for item in remediations]
            action["risk_flags"] = sorted(set(action.get("risk_flags", []) + material_flags + remediation_flags))
            ticket_id = action["ticket_id"]
            compliance_checks[ticket_id] = {
                "ticket_id": ticket_id,
                "compliance_status": status,
                "violations": violations,
                "remediations": remediations,
                "required_evidence_ids": required_evidence,
                "approval_state": action.get("approval_state", ApprovalState.DRAFT_RECOMMENDATION.value),
                "safe_rewrite": action["draft_response"],
            }
            evidence_ids.extend(required_evidence)
            risk_flags.extend(action["risk_flags"])
            material_risk_flags.extend(material_flags)

        context["compliance_checks"] = compliance_checks
        return {
            "summary": f"Checked {len(compliance_checks)} drafted responses against legal, regulatory, company, and evidence rules.",
            "compliance_checks": compliance_checks,
            "tools_used": ["deterministic_compliance_rules", "safe_rewrite_filter", "evidence_support_check"],
            "evidence_ids": sorted(set(evidence_ids)),
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.APPROVAL_REQUIRED.value if material_risk_flags else ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.91,
        }

    def _remove_internal_evidence(self, draft: str) -> str:
        marker = " Internal evidence:"
        if marker in draft:
            return draft.split(marker, 1)[0].strip() + " The case record includes the supporting evidence for review."
        marker = "Internal evidence:"
        if marker in draft:
            return draft.split(marker, 1)[0].strip() + " The case record includes the supporting evidence for review."
        return draft
