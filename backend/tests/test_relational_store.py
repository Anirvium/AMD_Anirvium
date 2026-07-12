from __future__ import annotations

import app.services.agent_runner as agent_runner_module
from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner
from app.services.relational_store import RelationalRepository


def _repository(tmp_path) -> RelationalRepository:  # type: ignore[no-untyped-def]
    return RelationalRepository(tmp_path / "sarvagun-test.sqlite3")


def test_relational_store_seeds_normalized_operational_and_evaluation_data(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)
    status = repository.relational_status()

    assert status["backend"] == "sqlite"
    assert status["schema_version"] == "sarvagun-operational-v1"
    assert status["normalized_operational_store"] is True
    assert status["foreign_keys"] is True
    assert status["foreign_key_violations"] == 0
    assert status["record_counts"]["customers"] == 6
    assert status["record_counts"]["cases"] >= 13
    assert status["record_counts"]["accounts"] == 6
    assert status["record_counts"]["transactions"] == 5
    assert status["record_counts"]["verification_records"] == 6
    assert status["record_counts"]["approval_requests"] == 6
    assert status["record_counts"]["escalations"] == 5
    assert status["record_counts"]["workflow_states"] == 13
    assert status["record_counts"]["evaluation_cases"] == 10
    assert status["evaluation_suite"] == "sarvagun-curated-eval-v1"
    assert status["external_benchmarks"] == {
        "tau_bench": False,
        "tau2_bench": False,
        "tau3": False,
    }


def test_relational_customer_and_case_queries_use_exact_normalized_filters(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)

    customer = repository.get_customer("CS-C002")
    assert customer is not None
    assert customer["customer_name"] == "Priya Shah"
    assert customer["total_case_count"] == 3
    assert customer["open_case_count"] == 3
    assert {row["customer_id"] for row in repository.list_customers(plan="pro", region="IN")} == {
        "CS-C002",
        "CS-C004",
    }

    financial_withdrawals = repository.list_cases(
        issue_type="withdrawal_processed_missing",
        queue="financial_operations",
    )
    assert {row["case_id"] for row in financial_withdrawals} == {
        "CASE-WDR-881",
        "CASE-WDR-912",
        "CS-002",
    }
    active_case = repository.get_case("CS-002")
    assert active_case is not None
    assert active_case["status"] == "OPEN"
    assert active_case["priority"] == "high"
    assert active_case["customer_name"] == "Priya Shah"
    assert repository.get_case("CASE-DOES-NOT-EXIST") is None


def test_operational_accounts_and_transactions_are_fk_linked_to_customer_and_case(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)

    account = repository.get_account("ACC-CS-002")
    transaction = repository.get_transaction("WDR-2291")
    withdrawals = repository.list_transactions(transaction_type="withdrawal")

    assert account is not None
    assert account["customer_id"] == "CS-C002"
    assert account["customer_name"] == "Priya Shah"
    assert account["transaction_count"] == 1
    assert transaction is not None
    assert transaction["transaction_id"] == "TXN-WDR-2291"
    assert transaction["customer_id"] == account["customer_id"]
    assert transaction["account_id"] == account["account_id"]
    assert transaction["case_id"] == "CS-002"
    assert transaction["issue_type"] == "withdrawal_processed_missing"
    assert transaction["state"] == "bank_trace_under_review"
    assert transaction["outcome_confirmed"] is False
    assert {row["transaction_id"] for row in withdrawals} == {
        "TXN-WDR-2291",
        "TXN-WDR-PRIORITY-901",
    }


def test_verification_approval_and_escalation_rows_form_coherent_case_chain(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)

    verification = repository.list_verification_records(case_id="CS-003")
    approval = repository.list_approval_requests(case_id="CS-003")
    escalation = repository.list_escalations(case_id="CS-003")

    assert len(verification) == len(approval) == len(escalation) == 1
    assert verification[0]["customer_id"] == approval[0]["customer_id"] == escalation[0]["customer_id"] == "CS-C003"
    assert verification[0]["account_id"] == "ACC-CS-003"
    assert verification[0]["status"] == "review_pending"
    assert approval[0]["approval_id"] == "APR-CS-003"
    assert approval[0]["approval_type"] == "restriction_removal"
    assert approval[0]["status"] == "REQUIRED"
    assert escalation[0]["approval_id"] == approval[0]["approval_id"]
    assert escalation[0]["destination"] == "verification_team"
    assert escalation[0]["status"] == "APPROVAL_REQUIRED"


def test_workflow_state_history_is_ordered_and_keeps_structured_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)
    states = repository.list_workflow_states(case_id="CS-002")

    assert [row["sequence"] for row in states] == [1, 2, 3]
    assert [row["state"] for row in states] == ["RECEIVED", "RECONTACT_DETECTED", "ESCALATED"]
    assert states[1]["entity_id"] == "TXN-WDR-2291"
    assert states[1]["metadata"]["related_cases"] == ["CASE-WDR-881", "CASE-WDR-912"]
    assert states[2]["metadata"]["escalation"] == "ESC-CS-002"


def test_relational_eval_cases_are_internal_synthetic_not_tau_claims(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)
    withdrawal_cases = repository.list_evaluation_cases(domain="withdrawals")

    assert len(withdrawal_cases) == 3
    assert all(row["source_suite"] == "sarvagun-curated-eval-v1" for row in withdrawal_cases)
    assert all(row["external_benchmark"] is None for row in withdrawal_cases)
    assert all(row["expected_evidence_ids"] for row in withdrawal_cases)
    assert all(row["unsafe_outputs"] for row in withdrawal_cases)
    assert all(row["metrics"] for row in withdrawal_cases)


def test_relational_run_persistence_is_idempotent_and_keeps_metrics_separate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)
    payload = {
        "run_id": "run_relational_test",
        "status": "completed",
        "metadata": {
            "created_at": "2026-07-12T10:00:00Z",
            "execution_mode": "hybrid",
            "conversation_id": "conv_relational_test",
        },
        "evaluation": {
            "metrics": {"overall_score": 88.5, "policy_compliance": 1.0},
            "diagnosis": [{"category": "repeat_contact"}],
            "recommendations": [{"recommendation_id": "OPT-TEST"}],
        },
        "sarvagun": {
            "customer_context": {
                "customer_id": "CS-C002",
                "customer_name": "Priya Shah",
                "plan": "pro",
                "region": "IN",
                "preferred_channel": "chat",
                "identity_status": "verified",
                "crm_account_id": "CRM-CS-002",
            },
            "conversation": {
                "conversation_id": "conv_relational_test",
                "message_type": "SUPPORT_QUERY",
            },
            "resolution_stage": "closed",
            "response_quality_gate": {"score": 1.0},
            "satisfaction": {
                "predicted_satisfaction": 0.48,
                "predicted_label": "dissatisfied",
                "explicit_csat": 2,
                "explicit_resolution": "partially",
            },
            "transcript": {
                "started_at": "2026-07-12T10:00:00Z",
                "ended_at": "2026-07-12T10:01:00Z",
                "turns": [
                    {
                        "turn_id": "turn_customer_test",
                        "role": "customer",
                        "content": "My withdrawal is missing.",
                        "created_at": "2026-07-12T10:00:00Z",
                        "delivery_status": "recorded",
                    },
                    {
                        "turn_id": "turn_agent_test",
                        "role": "agent",
                        "content": "I have escalated the evidence-backed review.",
                        "created_at": "2026-07-12T10:01:00Z",
                        "delivery_status": "recorded",
                    },
                ],
            },
            "tool_executions": [
                {
                    "tool_execution_id": "toolrun_relational_test",
                    "operation": "create_escalation",
                    "access_type": "write",
                    "status": "success",
                    "authorization": "mock_rbac_authorized",
                    "audit_id": "audit_relational_test",
                    "idempotency_key": "relational-test-idempotency",
                    "latency_ms": 2,
                    "simulated": True,
                    "result": {"escalation_id": "ESC-TEST"},
                    "error": None,
                }
            ],
        },
    }

    first = repository.persist_run_result(payload)
    second = repository.persist_run_result(payload)
    status = repository.relational_status()

    assert first["persisted"] is True
    assert second["persisted"] is True
    assert status["record_counts"]["runs"] == 1
    assert status["record_counts"]["evaluations"] == 1
    assert status["record_counts"]["tool_executions"] == 1
    assert status["record_counts"]["explicit_feedback"] == 1


def test_agent_runner_persists_relational_snapshot_without_replacing_json_store(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    repository = _repository(tmp_path)
    monkeypatch.setattr(agent_runner_module, "get_relational_repository", lambda: repository)
    runner = AgentRunner()
    result = runner.run(
        RunRequest(
            dataset="customer_support",
            selection_mode="selected",
            selected_ticket_ids=["CS-002"],
            customer_query="My processed withdrawal is still missing from my bank.",
        )
    )

    assert result.metadata["relational_persistence"]["persisted"] is True
    assert result.metadata["relational_persistence"]["run_id"] == result.run_id
    assert repository.relational_status()["record_counts"]["runs"] == 1
    assert repository.relational_status()["record_counts"]["evaluations"] == 1
    assert runner.logger.load_run(result.run_id) is not None
