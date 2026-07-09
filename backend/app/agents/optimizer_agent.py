from __future__ import annotations

from typing import Any, Dict

from app.schemas.trajectory import ApprovalState
from app.services.optimizer import OptimizationEngine


class OptimizerAgent:
    name = "Optimizer Agent"

    def __init__(self) -> None:
        self.engine = OptimizationEngine()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        recommendations = self.engine.recommend(context["diagnosis"], context["metrics"])
        context["recommendations"] = recommendations
        llm_optimizer_note = self._llm_optimizer_note(context)
        tools_used = ["optimization_rules", "workflow_change_mapper"]
        if llm_optimizer_note:
            tools_used.append("llm_optimizer_review")
        return {
            "summary": f"Generated {len(recommendations)} workflow optimization recommendations.",
            "recommendations": [item.model_dump() for item in recommendations],
            "llm_optimizer_note": llm_optimizer_note,
            "tools_used": tools_used,
            "evidence_ids": [],
            "risk_flags": [],
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.84,
        }

    def _llm_optimizer_note(self, context: Dict[str, Any]) -> str | None:
        llm_client = context.get("llm_client")
        if llm_client is None or getattr(llm_client, "model_name", "mock-trajectory-model") == "mock-trajectory-model":
            return None
        try:
            response = llm_client.generate(
                [
                    {"role": "system", "content": "You are an AI workflow optimizer. Return concise implementation priorities."},
                    {
                        "role": "user",
                        "content": (
                            f"Metrics: {context['metrics'].model_dump()}. "
                            f"Diagnosis: {[item.model_dump() for item in context['diagnosis']]}. "
                            "Suggest the top two workflow improvements."
                        ),
                    },
                ],
                temperature=0.1,
            )
        except Exception:
            return None
        return response.text.strip()[:1200] or None
