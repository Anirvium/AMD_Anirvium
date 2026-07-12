from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes_cx
from app.main import app
from app.services.capability_router import CapabilityRouter
from app.services.llm_client import LLMResponse
from app.services.relational_store import get_relational_repository


client = TestClient(app)


class FakeGeneralKnowledgeLLM:
    model_name = "amd-general-test-model"

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages, temperature=0.1):  # type: ignore[no-untyped-def]
        self.calls.append(messages)
        return LLMResponse(
            text="Photosynthesis converts light energy into chemical energy in plants.",
            model_name=self.model_name,
            tokens_in=20,
            tokens_out=12,
        )


def test_customer_directory_uses_real_seeded_relational_records() -> None:
    response = client.post("/conversations/turn", json={"message": "List all customers"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"]["requires_agent_run"] is False
    assert payload["capability_route"]["capability"] == "customer_directory"
    assert payload["capability_route"]["execution_path"] == "direct_relational_read"
    assert payload["capability_route"]["observed_by"] == "SuperTuriya"
    assert payload["direct_result"]["status"] == "success"
    assert payload["direct_result"]["record_count"] == len(get_relational_repository().list_customers())
    assert {row["customer_id"] for row in payload["direct_result"]["records"]} >= {"CS-C001", "CS-C002"}
    assert payload["signal"]["response"] == payload["direct_result"]["answer"]


def test_payment_failure_query_returns_seeded_cases_not_template_prose() -> None:
    response = client.post("/conversations/turn", json={"message": "Show all payment failure cases"})

    assert response.status_code == 200
    payload = response.json()
    result = payload["direct_result"]
    assert payload["capability_route"]["capability"] == "payment_failure_cases"
    assert result["record_count"] >= 2
    assert {row["issue_type"] for row in result["records"]} == {
        "deposit_missing",
        "withdrawal_processed_missing",
    }
    assert all(row["case_id"] in result["answer"] for row in result["records"])


def test_explicit_customer_and_case_lookups_are_typed_read_only_routes() -> None:
    customer_response = client.post("/conversations/turn", json={"message": "Get customer CS-C002"})
    case_response = client.post("/conversations/turn", json={"message": "Get case CS-002"})

    customer = customer_response.json()
    case = case_response.json()
    assert customer["capability_route"]["capability"] == "customer_lookup"
    assert customer["capability_route"]["read_only"] is True
    assert customer["direct_result"]["records"][0]["customer_name"] == "Priya Shah"
    assert customer["direct_result"]["aggregates"]["related_case_count"] >= 1
    assert case["capability_route"]["capability"] == "case_lookup"
    assert case["direct_result"]["records"][0]["case_id"] == "CS-002"
    assert case["direct_result"]["records"][0]["customer_id"] == "CS-C002"

    crm_response = client.post(
        "/conversations/turn",
        json={"message": "Get customer CRM-CS-002"},
    ).json()
    assert crm_response["capability_route"]["capability"] == "customer_lookup"
    assert crm_response["direct_result"]["records"][0]["customer_id"] == "CS-C002"


def test_explicit_case_id_resolves_without_case_or_ticket_keyword() -> None:
    response = client.post("/conversations/turn", json={"message": "Open CS-001"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["capability_route"]["capability"] == "case_lookup"
    assert payload["capability_route"]["execution_path"] == "direct_relational_read"
    assert payload["direct_result"]["status"] == "success"
    assert payload["direct_result"]["records"][0]["case_id"] == "CS-001"


def test_case_directory_returns_real_seeded_relational_records() -> None:
    response = client.post("/conversations/turn", json={"message": "List all cases"})

    assert response.status_code == 200
    payload = response.json()
    expected = get_relational_repository().list_cases(limit=500)
    assert payload["capability_route"]["capability"] == "case_directory"
    assert payload["capability_route"]["execution_path"] == "direct_relational_read"
    assert payload["direct_result"]["record_count"] == len(expected)
    assert {row["case_id"] for row in payload["direct_result"]["records"]} == {
        row["case_id"] for row in expected
    }


def test_open_payment_failure_query_applies_sqlite_status_filter() -> None:
    response = client.post("/conversations/turn", json={"message": "Show open payment-failure cases"})

    assert response.status_code == 200
    payload = response.json()
    result = payload["direct_result"]
    expected = sum(
        len(get_relational_repository().list_cases(issue_type=issue_type, status="OPEN", limit=500))
        for issue_type in ("deposit_missing", "withdrawal_processed_missing")
    )
    assert payload["capability_route"]["capability"] == "payment_failure_cases"
    assert result["aggregates"]["status_filter"] == "OPEN"
    assert result["record_count"] == expected
    assert all(row["status"] == "OPEN" for row in result["records"])


def test_case_directory_applies_sqlite_queue_filter() -> None:
    response = client.post(
        "/conversations/turn",
        json={"message": "Show cases assigned to financial operations queue"},
    )

    assert response.status_code == 200
    payload = response.json()
    result = payload["direct_result"]
    expected = get_relational_repository().list_cases(queue="financial_operations", limit=500)
    assert payload["capability_route"]["capability"] == "case_directory"
    assert result["aggregates"]["queue_filter"] == "financial_operations"
    assert result["record_count"] == len(expected)
    assert all(row["queue"] == "financial_operations" for row in result["records"])


def test_analytical_query_computes_counts_from_repository() -> None:
    response = client.post("/conversations/turn", json={"message": "How many payment failure cases are there?"})

    assert response.status_code == 200
    payload = response.json()
    result = payload["direct_result"]
    expected = sum(
        len(get_relational_repository().list_cases(issue_type=issue_type))
        for issue_type in ("deposit_missing", "withdrawal_processed_missing")
    )
    assert payload["capability_route"]["capability"] == "support_analytics"
    assert payload["capability_route"]["execution_path"] == "deterministic_analytics"
    assert result["aggregates"]["payment_failure_case_count"] == expected
    assert str(expected) in result["answer"]


def test_general_knowledge_uses_live_llm_path_without_business_records(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    llm = FakeGeneralKnowledgeLLM()
    router = CapabilityRouter(repository=get_relational_repository(), llm_client=llm)
    monkeypatch.setattr(routes_cx, "capability_router", router)

    response = client.post("/conversations/turn", json={"message": "Explain photosynthesis in one sentence"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["capability_route"]["capability"] == "general_knowledge"
    assert payload["capability_route"]["execution_path"] == "general_knowledge_llm"
    assert payload["direct_result"]["status"] == "success"
    assert payload["direct_result"]["generated_by"] == "live_llm:amd-general-test-model"
    assert payload["direct_result"]["records"] == []
    assert payload["direct_result"]["source_ids"] == []
    assert len(llm.calls) == 1
    assert "Photosynthesis" in payload["signal"]["response"]


def test_general_knowledge_mock_mode_is_truthful_and_support_query_still_routes_to_agents(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    router = CapabilityRouter(repository=get_relational_repository())
    monkeypatch.setattr(routes_cx, "capability_router", router)

    general_response = client.post("/conversations/turn", json={"message": "What is quantum entanglement?"})
    support_response = client.post("/conversations/turn", json={"message": "My UPI deposit is still missing"})

    general = general_response.json()
    support = support_response.json()
    assert general["capability_route"]["capability"] == "general_knowledge"
    if router.llm_client.model_name == "mock-trajectory-model":
        assert general["direct_result"]["status"] == "degraded"
        assert general["direct_result"]["fallback_reason"] == "live_llm_not_configured"
        assert "no live language model" in general["direct_result"]["answer"]
    assert support["capability_route"]["capability"] == "support_case_execution"
    assert support["capability_route"]["execution_path"] == "sarvagun_agent_pipeline"
    assert support["signal"]["requires_agent_run"] is True
    assert support["direct_result"] is None


def test_definition_of_support_term_is_general_but_personal_problem_stays_governed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    llm = FakeGeneralKnowledgeLLM()
    monkeypatch.setattr(
        routes_cx,
        "capability_router",
        CapabilityRouter(repository=get_relational_repository(), llm_client=llm),
    )

    definition = client.post("/conversations/turn", json={"message": "What is UPI?"}).json()
    personal = client.post("/conversations/turn", json={"message": "My UPI deposit is missing"}).json()

    assert definition["capability_route"]["capability"] == "general_knowledge"
    assert definition["signal"]["requires_agent_run"] is False
    assert personal["capability_route"]["capability"] == "support_case_execution"
    assert personal["signal"]["requires_agent_run"] is True


def test_conversation_session_retains_superturiya_observable_route_metadata() -> None:
    turn = client.post("/conversations/turn", json={"message": "List business plan customers"}).json()
    conversation = client.get(f"/conversations/{turn['signal']['conversation_id']}").json()

    stored = conversation["capability_routes"][-1]
    assert stored["route_id"] == turn["capability_route"]["route_id"]
    assert stored["capability"] == "customer_directory"
    assert stored["event_type"] == "capability.routed"
    assert stored["observed_by"] == "SuperTuriya"
    assert stored["record_count"] == turn["direct_result"]["record_count"]


def test_conversation_rejects_cross_customer_identity_switch() -> None:
    first = client.post(
        "/conversations/turn",
        json={"message": "Hi", "customer_id": "CS-C001"},
    ).json()

    switched = client.post(
        "/conversations/turn",
        json={
            "message": "Show my case",
            "conversation_id": first["signal"]["conversation_id"],
            "customer_id": "CS-C002",
        },
    )

    assert switched.status_code == 409
    assert "cannot switch customer identity" in switched.json()["detail"]


def test_support_route_and_correlation_are_linked_into_superturiya_events() -> None:
    correlation_id = "ui-linked-route-test"
    turn = client.post(
        "/conversations/turn",
        headers={"X-Correlation-ID": correlation_id},
        json={"message": "My UPI deposit is missing", "customer_id": "CS-C001"},
    ).json()

    run = client.post(
        "/runs",
        headers={"X-Correlation-ID": correlation_id},
        json={
            "dataset": "customer_support",
            "selection_mode": "selected",
            "selected_ticket_ids": ["CS-001"],
            "customer_id": "CS-C001",
            "conversation_id": turn["signal"]["conversation_id"],
            "customer_query": "My UPI deposit is missing",
        },
    )

    assert run.status_code == 200
    payload = run.json()
    route_events = [
        event for event in payload["superturiya"]["events"]
        if event["event_type"] == "capability.routed"
    ]
    assert len(route_events) == 1
    assert route_events[0]["correlation_id"] == correlation_id
    assert route_events[0]["payload"]["route_id"] == turn["capability_route"]["route_id"]
    assert route_events[0]["payload"]["capability"] == "support_case_execution"
