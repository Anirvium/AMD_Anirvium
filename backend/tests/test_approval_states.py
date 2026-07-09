from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_sensitive_actions_are_not_marked_final_without_approval() -> None:
    result = AgentRunner().run(
        RunRequest(selection_mode="selected", selected_ticket_ids=["T-001", "T-002", "T-004", "T-008"])
    )
    states = {action.ticket_id: action.approval_state for action in result.final_actions}

    assert states["T-001"] == "APPROVAL_REQUIRED"
    assert states["T-002"] == "APPROVAL_REQUIRED"
    assert states["T-004"] == "APPROVAL_REQUIRED"
    assert states["T-008"] == "APPROVAL_REQUIRED"


def test_critical_sla_case_gets_engineering_escalation_and_owner() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["T-001"]))
    action = result.final_actions[0]

    assert action.ticket_id == "T-001"
    assert "Engineering" in action.recommended_escalation
    assert action.owner
    assert action.urgency == "critical"
    assert "POL-003" in action.evidence_ids

