from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class HumanEscalationAgent:
    name = "Human Escalation Agent"

    def __init__(self, confidence_threshold: float = 0.45) -> None:
        self.confidence_threshold = confidence_threshold

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        handoffs: Dict[str, Dict[str, Any]] = {}
        risk_flags: List[str] = []
        evidence_ids: List[str] = []

        for action in context.get("final_actions", []):
            compliance = context.get("compliance_checks", {}).get(action["ticket_id"], {})
            base_confidence = float(action.get("confidence_score", 0.86))
            confidence = self._confidence_after_risk(base_confidence, action, compliance)
            status = compliance.get("compliance_status", action.get("compliance_status", "NOT_CHECKED"))
            approval_required = action.get("approval_state") == ApprovalState.APPROVAL_REQUIRED.value
            human_required = confidence < self.confidence_threshold or status in {"BLOCKED", "REVIEW_REQUIRED"} or approval_required

            reasons: List[str] = []
            if confidence < self.confidence_threshold:
                reasons.append("low_agent_confidence")
            if status in {"BLOCKED", "REVIEW_REQUIRED"}:
                reasons.append(f"compliance_{status.lower()}")
            if approval_required:
                reasons.append("approval_required")

            handoff_team = action.get("owner") if human_required else None
            handoff_reason = ", ".join(reasons) if reasons else None
            handoff_summary = None
            if human_required:
                handoff_summary = (
                    f"{action['ticket_id']} should be reviewed by {handoff_team}. "
                    f"Confidence {confidence:.2f}; reason: {handoff_reason}. "
                    f"Next action: {action.get('next_action', 'Review case context')}."
                )
                risk_flags.extend([reason.upper() for reason in reasons])

            action["confidence_score"] = round(confidence, 3)
            action["human_escalation_required"] = human_required
            action["handoff_team"] = handoff_team
            action["handoff_reason"] = handoff_reason
            action["handoff_summary"] = handoff_summary
            handoffs[action["ticket_id"]] = {
                "ticket_id": action["ticket_id"],
                "route": "human_required" if human_required else "agent_can_resolve",
                "team": handoff_team,
                "reason": handoff_reason,
                "confidence": round(confidence, 3),
                "handoff_summary": handoff_summary,
                "evidence_ids": action.get("evidence_ids", []),
            }
            evidence_ids.extend(action.get("evidence_ids", []))

        context["human_handoffs"] = handoffs
        return {
            "summary": f"Routed {sum(1 for item in handoffs.values() if item['route'] == 'human_required')} of {len(handoffs)} cases to human review.",
            "human_handoffs": handoffs,
            "confidence_threshold": self.confidence_threshold,
            "tools_used": ["confidence_gate", "human_queue_router", "handoff_summary_builder"],
            "evidence_ids": sorted(set(evidence_ids)),
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.ESCALATED.value if risk_flags else ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.89,
        }

    def _confidence_after_risk(self, base_confidence: float, action: Dict[str, Any], compliance: Dict[str, Any]) -> float:
        confidence = base_confidence
        if action.get("approval_state") == ApprovalState.APPROVAL_REQUIRED.value:
            confidence -= 0.18
        if compliance.get("compliance_status") == "REVIEW_REQUIRED":
            confidence -= 0.14
        if compliance.get("compliance_status") == "BLOCKED":
            confidence -= 0.36
        if action.get("urgency") == "critical":
            confidence -= 0.06
        if not action.get("evidence_ids"):
            confidence -= 0.22
        return max(0.0, min(1.0, confidence))
