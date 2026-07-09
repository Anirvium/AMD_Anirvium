from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_optimizer_emits_specific_metric_linked_recommendations() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="all_high_priority"))

    recommendations = result.evaluation.recommendations

    assert recommendations
    for recommendation in recommendations:
        assert recommendation.target_agent
        assert recommendation.problem
        assert recommendation.root_cause
        assert recommendation.fix
        assert recommendation.expected_metric_lift
        assert recommendation.implementation_hint
        assert recommendation.priority in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

