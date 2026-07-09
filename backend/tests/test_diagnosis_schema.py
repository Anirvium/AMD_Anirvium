from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_diagnosis_items_include_business_impact_and_metric_impact() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["T-002", "T-004"]))

    assert result.evaluation.diagnosis
    for item in result.evaluation.diagnosis:
        assert item.failure_type
        assert item.severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert item.affected_agent
        assert item.business_impact
        assert item.recommended_fix
        assert item.metric_impact
        assert 0 <= item.confidence <= 1

