from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState


class ReflectionAgent:
    name = "Reflection Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        reflections: List[Dict[str, Any]] = []
        risk_flags: List[str] = []

        for diagnosis in context.get("diagnosis", []):
            reflection = {
                "ticket_id": diagnosis.ticket_id,
                "target_agent": diagnosis.affected_agent,
                "repeated_mistake": diagnosis.failure_type in {
                    "MISSING_CUSTOMER_UPDATE_CADENCE",
                    "SENSITIVE_ACTION_WITHOUT_APPROVAL",
                    "LOW_CONFIDENCE_AGENT_STEP",
                },
                "reflection_score": round(max(0.2, 1.0 - diagnosis.confidence / 2), 3),
                "improvement": diagnosis.recommended_fix,
                "failure_type": diagnosis.failure_type,
                "metric_impact": diagnosis.metric_impact,
            }
            reflections.append(reflection)
            if reflection["repeated_mistake"]:
                risk_flags.append(f"REPEATED_{diagnosis.failure_type}")

        if not reflections:
            reflections.append(
                {
                    "ticket_id": None,
                    "target_agent": "Support Agent",
                    "repeated_mistake": False,
                    "reflection_score": 0.92,
                    "improvement": "No blocking issue found; keep collecting approval outcomes for calibration.",
                    "failure_type": "NO_BLOCKING_FAILURE",
                    "metric_impact": ["policy_compliance"],
                }
            )

        context["reflections"] = reflections
        return {
            "summary": f"Reflected on {len(reflections)} completed response quality signals.",
            "reflections": reflections,
            "tools_used": ["post_run_reflection_rules", "repeated_mistake_detector"],
            "evidence_ids": sorted({evidence_id for action in context.get("final_actions", []) for evidence_id in action.get("evidence_ids", [])}),
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.86,
        }
