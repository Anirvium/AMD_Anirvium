from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner


def test_customer_support_demo_reuses_completed_run() -> None:
    runner = AgentRunner()
    completed = runner.run(RunRequest(selection_mode="all_high_priority", dataset="customer_support"))
    runner.customer_support_demo_run_id = completed.run_id

    first = runner.get_or_create_customer_support_demo()
    second = runner.get_or_create_customer_support_demo()

    assert first["run"]["run_id"] == completed.run_id
    assert second["run"]["run_id"] == completed.run_id
