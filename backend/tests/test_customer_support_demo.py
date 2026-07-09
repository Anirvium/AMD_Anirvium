from __future__ import annotations

from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner
from app.services.data_loader import load_tickets


def test_customer_support_dataset_loads_real_use_case_tickets() -> None:
    tickets = load_tickets("customer_support")
    issue_types = {ticket.issue_type for ticket in tickets}

    assert len(tickets) == 6
    assert {"deposit_missing", "withdrawal_processed_missing", "verification_restriction"} <= issue_types
    assert any(ticket.expected_evidence_ids for ticket in tickets)


def test_customer_support_run_uses_curated_kb_evidence() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="all_high_priority", dataset="customer_support"))
    used_evidence = {evidence_id for action in result.final_actions for evidence_id in action.evidence_ids}
    approval_states = {action.ticket_id: action.approval_state for action in result.final_actions}

    assert result.metadata["dataset"] == "customer_support"
    assert any(evidence_id.startswith("POL-CS-") for evidence_id in used_evidence)
    assert approval_states["CS-003"] == "APPROVAL_REQUIRED"
    assert approval_states["CS-006"] == "APPROVAL_REQUIRED"
    assert any(action.human_escalation_required for action in result.final_actions)
    assert result.evaluation.details["human_handoff_count"] >= 1
