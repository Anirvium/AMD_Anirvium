from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_agent_runner_generates_full_multi_agent_trajectory() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="all_high_priority"))

    assert result.status == "completed"
    assert len(result.selected_ticket_ids) == 5
    assert len(result.trajectory) == 12
    assert result.graph.nodes[0].label == "Attachment Evidence Agent"
    assert result.graph.edges[-1].target == "step_012"
    assert len(result.final_actions) == 5
    agent_names = [span.agent_name for span in result.trajectory]
    assert "Compliance Agent" in agent_names
    assert "Human Escalation Agent" in agent_names
    assert "Reflection Agent" in agent_names
    assert "Learning Extraction Agent" in agent_names
    assert result.visual_evidence_cards
    assert result.evaluation.recommendations
    assert result.evaluation.details["agent_step_count"] == 12
    assert "compliance_decision" in result.metadata["observability"]["event_sources"]


def test_agent_runner_promotes_attachments_to_evidence_cards() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["T-001"]))

    assert result.visual_evidence_cards
    assert result.visual_evidence_cards[0].evidence_id.startswith("VIS-")
    assert result.visual_evidence_cards[0].requires_policy_check is True
    assert result.visual_evidence_cards[0].evidence_id in result.final_actions[0].evidence_ids
    assert result.visual_evidence_cards[0].model_name == "deterministic-attachment-evidence"
    assert result.final_actions[0].compliance_status in {"PASS", "REVIEW_REQUIRED", "BLOCKED"}
    assert 0.0 <= result.final_actions[0].confidence_score <= 1.0


def test_agent_runner_marks_sensitive_actions_for_approval() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["T-002", "T-004"]))
    states = {action.ticket_id: action.approval_state for action in result.final_actions}
    handoffs = {action.ticket_id: action.human_escalation_required for action in result.final_actions}

    assert states["T-002"] == "APPROVAL_REQUIRED"
    assert states["T-004"] == "APPROVAL_REQUIRED"
    assert handoffs["T-002"] is True
    assert handoffs["T-004"] is True
