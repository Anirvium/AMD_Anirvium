from __future__ import annotations

from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner
from app.services.memory import (
    add_long_term_memory,
    add_mid_term_summary,
    add_short_term_memory,
    get_mid_term_memory,
    get_short_term_memory,
    memory_status,
    search_long_term_memory,
)
from app.services.vector_store import vector_status


def test_short_mid_and_long_term_memory_paths() -> None:
    add_short_term_memory("session-a", "Customer asked about withdrawal status.", role="customer")
    add_mid_term_summary("session-a", "Customer has a repeated withdrawal concern.")
    add_long_term_memory("LTM-test-withdrawal", "Withdrawal status requires evidence and bank proof.", metadata={"title": "Withdrawal memory"})

    assert get_short_term_memory("session-a")[0]["role"] == "customer"
    assert get_mid_term_memory("session-a")[0]["summary"].startswith("Customer has")
    assert search_long_term_memory("withdrawal bank proof", limit=5)
    assert memory_status()["memory_backend"] == "local"


def test_agent_runner_indexes_trajectory_memory() -> None:
    result = AgentRunner().run(RunRequest(selection_mode="selected", selected_ticket_ids=["CS-002"], dataset="customer_support"))
    status = vector_status()

    assert result.metadata["dataset"] == "customer_support"
    assert status["local_index_sizes"]["trajectory"] >= 1
    assert status["local_index_sizes"]["memory"] >= 1
