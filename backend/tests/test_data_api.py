from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_data_api_exposes_exact_synthetic_operational_records() -> None:
    customers = client.get("/data/customers")
    cases = client.get("/data/cases", params={"status": "OPEN", "queue": "financial_operations"})
    transactions = client.get("/data/transactions", params={"transaction_type": "withdrawal"})

    assert customers.status_code == cases.status_code == transactions.status_code == 200
    assert customers.json()["count"] == 6
    assert all(row["status"] == "OPEN" for row in cases.json()["records"])
    assert all(row["queue"] == "financial_operations" for row in cases.json()["records"])
    assert {row["transaction_id"] for row in transactions.json()["records"]} == {
        "TXN-WDR-2291",
        "TXN-WDR-PRIORITY-901",
    }


def test_case_context_joins_customer_transaction_approval_escalation_and_workflow() -> None:
    response = client.get("/data/cases/CS-002/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["synthetic_data_only"] is True
    assert payload["case"]["customer_id"] == payload["customer"]["customer_id"] == "CS-C002"
    assert payload["accounts"][0]["account_id"] == "ACC-CS-002"
    assert payload["transactions"][0]["reference"] == "WDR-2291"
    assert payload["approval_requests"][0]["approval_id"] == "APR-CS-002"
    assert payload["escalations"][0]["escalation_id"] == "ESC-CS-002"
    assert [row["state"] for row in payload["workflow_states"]] == [
        "RECEIVED",
        "RECONTACT_DETECTED",
        "ESCALATED",
    ]


def test_data_api_returns_404_for_unknown_case_or_customer() -> None:
    assert client.get("/data/customers/CS-C999").status_code == 404
    assert client.get("/data/cases/CS-999/context").status_code == 404
