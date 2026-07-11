from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState, TrajectorySpan
from app.services.diagnosis import FailureDiagnosisEngine
from app.services.evaluator import EvaluationEngine
from app.services.model_router import ModelRole


class CriticEvaluatorAgent:
    name = "Critic / Evaluator Agent"

    def __init__(self) -> None:
        self.evaluator = EvaluationEngine()
        self.diagnosis_engine = FailureDiagnosisEngine()

    def run(self, context: Dict[str, Any], spans: List[TrajectorySpan]) -> Dict[str, Any]:
        metrics = self.evaluator.score(context, spans)
        diagnosis = self.diagnosis_engine.diagnose(context, metrics, spans)
        context["metrics"] = metrics
        context["diagnosis"] = diagnosis
        llm_client = context.get("llm_client")
        model_router = context.get("model_router")
        model_name = getattr(llm_client, "model_name", None) or (
            model_router.route(ModelRole.CRITIC_AGENT).model_name
            if model_router
            else "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        )
        llm_review = self._llm_review(context) if context.get("enable_auxiliary_llm_reviews", False) else None
        tools_used = ["deterministic_eval_rules", "failure_diagnosis_engine"]
        if llm_review:
            tools_used.append("llm_critic_review")
        return {
            "summary": f"Scored trajectory at {metrics.overall_score}/100 with {len(diagnosis)} diagnosis items.",
            "metrics": metrics.model_dump(),
            "diagnosis": [item.model_dump() for item in diagnosis],
            "llm_review": llm_review,
            "tools_used": tools_used,
            "evidence_ids": sorted({evidence_id for action in context.get("final_actions", []) for evidence_id in action.get("evidence_ids", [])}),
            "risk_flags": [item.category.upper() for item in diagnosis if item.severity in {"HIGH", "CRITICAL"}],
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "model_name": model_name if llm_review else "deterministic-trajectory-evaluator-v1",
            "confidence": 0.87,
        }

    def _llm_review(self, context: Dict[str, Any]) -> str | None:
        llm_client = context.get("llm_client")
        if llm_client is None or getattr(llm_client, "model_name", "mock-trajectory-model") == "mock-trajectory-model":
            return None
        try:
            response = llm_client.generate(
                [
                    {"role": "system", "content": "You are a strict trajectory critic. Return a short risk review."},
                    {
                        "role": "user",
                        "content": (
                            "Review these final support actions for evidence grounding, missing approvals, "
                            f"and unsafe promises: {context.get('final_actions', [])}"
                        ),
                    },
                ],
                temperature=0.0,
            )
        except Exception:
            return None
        return response.text.strip()[:1200] or None
