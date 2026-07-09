from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_evaluator_scores_policy_and_evidence_grounding() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["T-001", "T-002"]))

    metrics = result.evaluation.metrics

    assert metrics.overall_score >= 80
    assert metrics.evidence_grounding >= 0.9
    assert metrics.policy_compliance == 1.0
    assert metrics.escalation_quality == 1.0
    assert metrics.hallucination_risk < 0.25


def test_customer_support_financial_cases_require_policy_approval() -> None:
    result = AgentRunner().run(
        RunRequest(selection_mode="selected", selected_ticket_ids=["CS-001", "CS-002"], dataset="customer_support")
    )

    metrics = result.evaluation.metrics

    assert metrics.policy_compliance == 1.0
    assert all(action.approval_state == "APPROVAL_REQUIRED" for action in result.final_actions)
