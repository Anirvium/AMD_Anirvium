from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_all_metric_scores_are_within_valid_bounds() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="all"))
    metrics = result.evaluation.metrics.model_dump()

    for metric_name, value in metrics.items():
        if metric_name == "overall_score":
            assert 0 <= value <= 100
        else:
            assert 0 <= value <= 1


def test_trajectory_spans_include_observability_fields() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["T-001"]))

    assert result.trajectory
    for span in result.trajectory:
        assert span.run_id
        assert span.step_id
        assert span.agent_name
        assert span.input_summary
        assert span.output_summary
        assert span.latency_ms >= 0
        assert span.tokens_in > 0
        assert span.tokens_out > 0
        assert 0 <= span.confidence <= 1
        assert span.timestamp

