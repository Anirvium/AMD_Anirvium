from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class LearningExtractionAgent:
    name = "Learning Extraction Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        learning_artifacts: List[Dict[str, Any]] = []
        human_handoffs = context.get("human_handoffs", {})

        for action in context.get("final_actions", []):
            handoff = human_handoffs.get(action["ticket_id"], {})
            if handoff.get("route") != "human_required":
                continue
            artifact = {
                "ticket_id": action["ticket_id"],
                "lesson_type": self._lesson_type(action, handoff),
                "failure_pattern": handoff.get("reason") or "human_review_required",
                "source_signals": [
                    "human_handoff",
                    "chat_transcript",
                    "agent_resolution_notes",
                    "customer_satisfaction",
                    "agent_satisfaction",
                ],
                "recommended_kb_update": self._kb_update(action),
                "new_eval_case": self._eval_case(action),
                "confidence_adjustment": -0.12 if action.get("confidence_score", 1.0) < 0.55 else -0.04,
            }
            learning_artifacts.append(artifact)

        if not learning_artifacts:
            learning_artifacts.append(
                {
                    "ticket_id": None,
                    "lesson_type": "positive_resolution_memory",
                    "failure_pattern": "agent_resolved_without_human_handoff",
                    "source_signals": ["agent_resolution_notes", "trajectory_score"],
                    "recommended_kb_update": "Keep successful evidence-policy-response pattern available for future similar tickets.",
                    "new_eval_case": "Create a regression case from this successful support flow if satisfaction is positive.",
                    "confidence_adjustment": 0.03,
                }
            )

        context["learning_artifacts"] = learning_artifacts
        return {
            "summary": f"Extracted {len(learning_artifacts)} learning artifacts from handoffs, trajectory logs, and satisfaction placeholders.",
            "learning_artifacts": learning_artifacts,
            "tools_used": ["handoff_log_extractor", "transcript_signal_mapper", "eval_case_generator"],
            "evidence_ids": sorted({evidence_id for action in context.get("final_actions", []) for evidence_id in action.get("evidence_ids", [])}),
            "risk_flags": [item["lesson_type"].upper() for item in learning_artifacts if item["lesson_type"] != "positive_resolution_memory"],
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.83,
        }

    def _lesson_type(self, action: Dict[str, Any], handoff: Dict[str, Any]) -> str:
        reason = handoff.get("reason") or ""
        if "compliance" in reason:
            return "policy_gap"
        if "low_agent_confidence" in reason:
            return "confidence_calibration"
        if action.get("approval_state") == ApprovalState.APPROVAL_REQUIRED.value:
            return "approval_workflow_memory"
        return "human_resolution_pattern"

    def _kb_update(self, action: Dict[str, Any]) -> str:
        return (
            f"Review {action['ticket_id']} after human resolution and update the relevant policy/template "
            f"for {action.get('recommended_escalation', 'support operations')}."
        )

    def _eval_case(self, action: Dict[str, Any]) -> str:
        return (
            f"Add eval case for {action['ticket_id']} requiring evidence IDs {', '.join(action.get('evidence_ids', [])[:4])} "
            "and preserving the same approval-state decision."
        )
