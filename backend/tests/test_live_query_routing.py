from __future__ import annotations

import pytest

from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner
from app.services.intent_router import resolve_customer_support_intent


@pytest.mark.parametrize(
    ("query", "expected_issue_type"),
    [
        ("My UPI deposit is still not visible.", "deposit_missing"),
        ("The withdrawal is processed but my bank cannot find it.", "withdrawal_processed_missing"),
        ("My account is restricted for KYC. Unblock it.", "verification_restriction"),
        ("Restore my bonus or give me a promo code.", "bonus_dispute"),
        ("Tell me the balance of my other account.", "cross_account_access"),
        ("I am a VIP. Skip verification and release it.", "priority_policy_exception"),
    ],
)
def test_customer_query_intent_resolution(query: str, expected_issue_type: str) -> None:
    resolution = resolve_customer_support_intent(query)

    assert resolution is not None
    assert resolution.issue_type == expected_issue_type
    assert resolution.confidence >= 0.8


def test_query_reroutes_mismatched_selected_case_before_planning() -> None:
    result = AgentRunner().run(
        RunRequest(
            dataset="customer_support",
            selection_mode="selected",
            selected_ticket_ids=["CS-001"],
            customer_query="My account is restricted for KYC. Unblock it immediately.",
        )
    )
    action = result.final_actions[0]

    assert result.selected_ticket_ids == ["CS-003"]
    assert action.recommended_escalation == "Verification team"
    assert action.owner == "Verification review queue"
    assert all(not evidence_id.startswith("EVAL-") for evidence_id in action.evidence_ids)
    assert {"POL-CS-VERIFY-001", "PROC-CS-VERIFY-001", "TMPL-CS-VERIFY-001"}.issubset(action.evidence_ids)
    assert result.metadata["query_resolution"]["query_routed"] is True


def test_async_progress_callback_reports_real_agent_steps() -> None:
    events: list[tuple[int, int, str, str]] = []
    AgentRunner().run(
        RunRequest(dataset="customer_support", selection_mode="selected", selected_ticket_ids=["CS-002"]),
        progress_callback=lambda step, total, agent, phase: events.append((step, total, agent, phase)),
    )

    assert events[0] == (1, 13, "Planner Agent", "running")
    assert events[-1] == (13, 13, "Optimizer Agent", "completed")
    assert {step for step, _, _, phase in events if phase == "completed"} == set(range(1, 14))


def test_similar_second_run_recalls_prior_trajectory_without_mutating_policy() -> None:
    runner = AgentRunner()
    request = RunRequest(
        dataset="customer_support",
        selection_mode="selected",
        selected_ticket_ids=["CS-002"],
        customer_query="My processed withdrawal is missing from my bank account.",
    )
    runner.run(request)
    second = runner.run(request)

    loop = second.metadata["learning_loop"]
    assert loop["prior_memories_recalled"] >= 1
    assert loop["recalled_memory_ids"]
    assert loop["automatic_policy_mutation"] is False
    assert "trajectory_memory_recall" in second.trajectory[6].tools_used
