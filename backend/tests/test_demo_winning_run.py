from fastapi.testclient import TestClient

from app.main import app


def test_demo_winning_run_endpoint_returns_complete_demo() -> None:
    client = TestClient(app)

    response = client.get("/demo/winning-run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario"]["primary_ticket_id"] == "T-001"
    assert {ticket["ticket_id"] for ticket in payload["selected_tickets"]} >= {"T-001", "T-002", "T-004", "T-008"}
    assert payload["primary_ticket_result"]["recommended_escalation"] == "Engineering incident response + Customer Success"
    assert payload["primary_ticket_result"]["approval_state"] == "APPROVAL_REQUIRED"
    assert payload["visual_evidence_cards"]
    assert any(card["evidence_id"].startswith("VIS-") for card in payload["visual_evidence_cards"])
    assert payload["evaluation"]["metrics"]["overall_score"] > 80
    assert payload["failure_diagnosis"]
    assert payload["optimization_recommendations"]
    assert payload["amd_benchmark_readiness_metadata"]["status"] == "AMD execution pending"
    assert payload["amd_benchmark_readiness_metadata"]["real_evidence_available"] is False
