from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.services.sarvagun_lifecycle as lifecycle_module
import app.services.vector_store as vector_store
from app.main import app
from app.schemas.cx import AssuranceCommitment, CustomerContext, EmotionSignal, EscalationEvent, RecontactAnalysis
from app.schemas.run import RunRequest
from app.services.agent_runner import AgentRunner
from app.services.conversation import conversation_manager
from app.services.customer_connectors import MockConnector, ToolExecutor
from app.services.graph_discovery import build_trajectory_property_graph
from app.services.runtime import get_agent_runner
from app.services.sarvagun_lifecycle import EmergingIncidentDetector, ResponseQualityGate


client = TestClient(app)

_AUTONOMOUS_TOOL_ALLOWLIST = {
    "mock_customer_system.get_open_cases",
    "mock_customer_system.get_interaction_history",
    "mock_customer_system.lookup_operational_status",
    "mock_customer_system.create_escalation",
    "superturiya.trajectory_memory_search",
}


def _cx_request(mode: str = "hybrid") -> RunRequest:
    return RunRequest(
        dataset="customer_support",
        selection_mode="selected",
        selected_ticket_ids=["CS-002"],
        customer_query=(
            "This is my third contact. My withdrawal is processed but the bank has not received it, "
            "nobody replied to the promised update, and I am extremely frustrated."
        ),
        execution_mode=mode,  # type: ignore[arg-type]
    )


def _quality_gate_context() -> tuple[
    CustomerContext,
    EmotionSignal,
    RecontactAnalysis,
    EscalationEvent,
    AssuranceCommitment,
]:
    return (
        CustomerContext(customer_id="TEST-CUSTOMER", customer_name="Priya", plan="pro"),
        EmotionSignal(
            primary_emotion="neutral",
            intensity=0.2,
            irritation_detected=False,
            repeat_contact_contribution=0.0,
            requires_acknowledgement=False,
            requires_apology=False,
            escalation_risk=0.1,
        ),
        RecontactAnalysis(customer_id="TEST-CUSTOMER", current_issue="withdrawal_processed_missing"),
        EscalationEvent(
            escalation_id="ESC-QUALITY-1",
            reason="standard_support_route",
            severity="low",
            destination="financial_operations",
            sla_minutes=60,
            status="RECOMMENDED",
        ),
        AssuranceCommitment(
            assurance_given=True,
            assurance_type="ownership",
            assurance_text="I have documented the complete case history for the responsible support team.",
            supported_by=["POL-CS-PAY-002"],
            commitment_owner="Withdrawal review queue",
            fulfilment_status="documented",
        ),
    )


def test_backend_conversation_manager_handles_greeting_without_full_run() -> None:
    response = client.post("/conversations/turn", json={"message": "Hi"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"]["message_type"] == "GREETING"
    assert payload["signal"]["requires_agent_run"] is False
    assert "Sarvagun" in payload["signal"]["response"]
    assert [turn["role"] for turn in payload["turns"]] == ["customer", "agent"]


def test_backend_conversation_manager_routes_support_query() -> None:
    response = client.post("/conversations/turn", json={"message": "My UPI deposit is missing."})

    assert response.status_code == 200
    signal = response.json()["signal"]
    assert signal["message_type"] == "SUPPORT_QUERY"
    assert signal["requires_agent_run"] is True


@pytest.mark.parametrize("mode", ["policy_driven", "plan_driven", "autonomous", "hybrid"])
def test_sarvagun_supports_all_governed_execution_modes(mode: str) -> None:
    result = AgentRunner().run(_cx_request(mode))

    assert result.sarvagun is not None
    assert result.superturiya is not None
    strategy = result.sarvagun.execution_strategy
    assert strategy.execution_mode == mode
    assert strategy.policy_guardian == "deterministic_policy_and_compliance_gates"
    assert strategy.maximum_agent_steps == 13
    assert strategy.replan_limit == 1
    assert set(strategy.selected_tools) <= _AUTONOMOUS_TOOL_ALLOWLIST
    assert {
        "unsupported_commitment_without_evidence",
        "policy_or_identity_bypass",
        "unauthorized_enterprise_write",
        "maximum_agent_steps_exceeded",
    } <= set(strategy.stop_conditions)
    if mode in {"autonomous", "hybrid"}:
        assert 0 < len(strategy.autonomous_decisions) <= strategy.replan_limit + 1
        assert [decision["iteration"] for decision in strategy.autonomous_decisions] == list(
            range(1, len(strategy.autonomous_decisions) + 1)
        )
        assert all(decision["policy_supervisor"] == "accepted" for decision in strategy.autonomous_decisions)
        assert all(
            set(decision.get("selected_tools", [])) <= _AUTONOMOUS_TOOL_ALLOWLIST
            for decision in strategy.autonomous_decisions
        )
    else:
        assert strategy.autonomous_decisions == []
    assert len(result.trajectory) == 13
    assert result.metadata["system_identity"] == {
        "platform": "Anirvium AI",
        "execution_system": "Sarvagun",
        "intelligence_system": "SuperTuriya",
    }
    assert result.final_actions[0].approval_state == "APPROVAL_REQUIRED"


def test_execution_mode_cannot_weaken_financial_policy_or_handoff() -> None:
    snapshots: list[str] = []
    for mode in ("policy_driven", "plan_driven", "autonomous", "hybrid"):
        result = AgentRunner().run(_cx_request(mode))
        policy_span = next(span for span in result.trajectory if span.agent_name == "Policy Checker Agent")
        policy_check = policy_span.full_output["policy_checks"]["CS-002"]
        action = result.final_actions[0]
        snapshots.append(
            json.dumps(
                {
                    "approval_state": action.approval_state,
                    "compliance_status": action.compliance_status,
                    "human_escalation_required": action.human_escalation_required,
                    "policy_approval_state": policy_check["approval_state"],
                    "constraints": policy_check["constraints"],
                    "risk_flags": policy_check["risk_flags"],
                },
                sort_keys=True,
            )
        )

    assert len(set(snapshots)) == 1
    policy_snapshot = json.loads(snapshots[0])
    assert policy_snapshot["approval_state"] == "APPROVAL_REQUIRED"
    assert policy_snapshot["human_escalation_required"] is True
    assert "FINANCIAL_REVIEW_APPROVAL_REQUIRED" in policy_snapshot["risk_flags"]


def test_sarvagun_closes_full_cx_operations_lifecycle() -> None:
    result = AgentRunner().run(_cx_request())
    assert result.sarvagun is not None
    cx = result.sarvagun

    assert cx.customer_context.customer_id == "CS-C002"
    assert cx.customer_context.customer_name == "Priya Shah"
    assert cx.emotion.primary_emotion == "frustration"
    assert cx.emotion.requires_apology is True
    assert cx.recontact.recontact_detected is True
    assert cx.recontact.previous_commitment_missed is True
    assert cx.recontact.contacts_last_7_days == 3
    assert cx.incident.detected is True
    assert cx.incident.unique_customers == 6
    assert cx.escalation.destination == "incident_manager"
    assert cx.escalation.status == "ESCALATED"
    assert {tool.operation for tool in cx.tool_executions}.issuperset(
        {"find_customer", "get_open_cases", "get_interaction_history", "lookup_operational_status", "create_escalation", "add_case_note", "attach_transcript"}
    )
    assert all(tool.authorization == "mock_rbac_authorized" for tool in cx.tool_executions)
    assert all(tool.simulated is True for tool in cx.tool_executions)
    assert cx.assurances[0].assurance_type == "ownership"
    assert cx.assurances[0].supported_by
    assert cx.assurances[0].assurance_text in result.final_actions[0].draft_response
    assert cx.satisfaction.explicit_csat is None
    assert cx.satisfaction.predicted_label == "dissatisfied"
    assert cx.satisfaction.rubric["empathy"] == 1.0
    assert cx.transcript.turns[0].role == "customer"
    assert cx.transcript.turns[-1].role == "agent"
    assert cx.transcript.redaction_status == "synthetic_data_no_pii"


def test_response_quality_gate_runs_after_compliance_has_checked_the_action() -> None:
    result = AgentRunner().run(_cx_request())
    assert result.sarvagun is not None
    assert result.superturiya is not None

    action = result.final_actions[0]
    gate = result.sarvagun.response_quality_gate
    compliance_span = next(span for span in result.trajectory if span.agent_name == "Compliance Agent")
    compliance_check = compliance_span.full_output["compliance_checks"][action.ticket_id]

    assert action.compliance_status != "NOT_CHECKED"
    assert compliance_check["compliance_status"] == action.compliance_status
    assert gate.checks["policy_checked"] is True
    assert any(event.event_type == "response.quality_checked" for event in result.superturiya.events)


def test_response_quality_gate_rewrites_deterministic_fallback_concisely_and_preserves_assurance() -> None:
    customer, emotion, recontact, escalation, assurance = _quality_gate_context()
    action = {
        "ticket_id": "CS-QUALITY-1",
        "draft_response": "Verbose deterministic fallback. " * 80,
        "evidence_ids": ["POL-CS-PAY-002"],
        "compliance_status": "PASS",
        "approval_state": "DRAFT_RECOMMENDATION",
        "generation_source": "deterministic_safe_fallback",
        "owner": "Withdrawal review queue",
    }

    final, gate = ResponseQualityGate().evaluate(
        action=action,
        customer=customer,
        emotion=emotion,
        recontact=recontact,
        escalation=escalation,
        assurance=assurance,
        tools=[],
    )

    assert gate.decision == "rewritten"
    assert gate.rewrite_applied is True
    assert gate.original_length > 900
    assert 40 <= gate.final_length == len(final) <= 900
    assert gate.checks["concise_enough"] is True
    assert final.count(assurance.assurance_text) == 1


def test_response_quality_gate_rejects_unsafe_guarantee_and_private_reasoning() -> None:
    customer, emotion, recontact, escalation, assurance = _quality_gate_context()
    action = {
        "ticket_id": "CS-QUALITY-2",
        "draft_response": (
            "<think>Hidden reasoning from the system prompt and chain of thought.</think> "
            "Your refund definitely will be approved and will be refunded today."
        ),
        "evidence_ids": ["POL-CS-PAY-002"],
        "compliance_status": "PASS",
        "approval_state": "DRAFT_RECOMMENDATION",
        "generation_source": "amd_vllm",
        "owner": "Withdrawal review queue",
    }

    final, gate = ResponseQualityGate().evaluate(
        action=action,
        customer=customer,
        emotion=emotion,
        recontact=recontact,
        escalation=escalation,
        assurance=assurance,
        tools=[],
    )
    lowered = final.lower()

    assert gate.decision == "rewritten"
    assert gate.rewrite_applied is True
    assert gate.checks["no_unsupported_outcome_guarantee"] is True
    assert gate.checks["no_private_reasoning"] is True
    assert all(term not in lowered for term in ("<think>", "system prompt", "chain of thought", "hidden reasoning"))
    assert all(term not in lowered for term in ("definitely", "will be approved", "will be refunded"))
    assert final.count(assurance.assurance_text) == 1


def test_direct_agent_runner_records_current_customer_turn_exactly_once() -> None:
    conversation_id = f"conv-direct-{uuid4().hex}"
    customer_query = (
        f"Direct run {uuid4().hex}: my withdrawal is processed but the bank has not received it."
    )
    result = AgentRunner().run(
        RunRequest(
            dataset="customer_support",
            selection_mode="selected",
            selected_ticket_ids=["CS-002"],
            customer_query=customer_query,
            conversation_id=conversation_id,
        )
    )
    assert result.sarvagun is not None

    transcript_matches = [
        turn for turn in result.sarvagun.transcript.turns
        if turn.role == "customer" and turn.content == customer_query
    ]
    session = conversation_manager.get_session(conversation_id)
    assert session is not None
    session_matches = [
        turn for turn in session["turns"]
        if turn["role"] == "customer" and turn["content"] == customer_query
    ]

    assert len(transcript_matches) == 1
    assert len(session_matches) == 1


def test_superturiya_observes_evaluates_and_creates_memory() -> None:
    result = AgentRunner().run(_cx_request())
    assert result.superturiya is not None
    intelligence = result.superturiya

    assert intelligence.observed_system == "Sarvagun"
    assert intelligence.feedback_loop_status == "closed"
    assert intelligence.trace_count == 13
    assert intelligence.event_count >= 20
    assert {"observe", "trace", "discover", "evaluate", "diagnose", "recommend", "store", "recall", "improve"}.issubset(intelligence.lifecycle)
    assert len(intelligence.created_memory_ids) == 3
    assert intelligence.automatic_policy_mutation is False
    assert intelligence.discovered_path[0] == "Planner Agent"
    assert intelligence.discovered_path[-1] == "Optimizer Agent"


def test_second_run_applies_first_run_intelligence_without_mutating_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vector_store, "_LOCAL_INDEXES", {})
    runner = AgentRunner()
    first = runner.run(_cx_request())
    second = runner.run(_cx_request())
    assert first.sarvagun is not None
    assert second.sarvagun is not None
    assert second.superturiya is not None

    assert first.sarvagun.execution_strategy.recalled_intelligence_ids == []
    strategy = second.sarvagun.execution_strategy
    assert strategy.recalled_intelligence_ids
    assert f"LTM-{first.run_id}" in strategy.recalled_intelligence_ids
    assert "review_prior_failure_patterns_before_planning" in strategy.memory_influenced_decisions
    assert second.superturiya.applied_memory_ids == strategy.recalled_intelligence_ids
    assert "superturiya.memory_guidance" in second.trajectory[0].tools_used
    assert first.final_actions[0].approval_state == second.final_actions[0].approval_state == "APPROVAL_REQUIRED"
    assert second.superturiya.automatic_policy_mutation is False
    assert second.metadata["learning_loop"]["reuse_stage"] == "pre_plan_strategy_and_response_drafting"


def test_mock_connector_write_is_idempotent_and_audited() -> None:
    connector = MockConnector()
    executor = ToolExecutor(connector)
    idempotency_key = f"test-create-escalation-{uuid4().hex}"
    first = executor.execute(
        "create_escalation",
        "CASE-TEST-1",
        {"reason": "repeat_contact", "status": "ESCALATED"},
        idempotency_key=idempotency_key,
    )
    second = executor.execute(
        "create_escalation",
        "CASE-TEST-1",
        {"reason": "repeat_contact", "status": "ESCALATED"},
        idempotency_key=idempotency_key,
    )

    assert first.status == "success"
    assert second.status == "reused"
    assert second.tool_execution_id == first.tool_execution_id
    assert second.audit_id == first.audit_id
    assert second.result == first.result
    assert first.audit_id
    assert first.access_type == "write"
    assert first.before_state == {}
    assert first.after_state["case_id"] == "CASE-TEST-1"
    assert len(connector.escalations) == 1


def test_mock_connector_does_not_execute_write_while_approval_is_pending() -> None:
    connector = MockConnector()
    executor = ToolExecutor(connector)
    pending = executor.execute(
        "create_escalation",
        "CASE-PENDING-1",
        {"reason": "financial_exception", "status": "APPROVAL_REQUIRED"},
        idempotency_key=f"test-pending-escalation-{uuid4().hex}",
        approval_required=True,
        approved=False,
    )

    assert pending.status == "approval_required"
    assert pending.authorization == "authorized_but_approval_pending"
    assert pending.result == {}
    assert pending.after_state == {}
    assert connector.escalations == {}


def test_mock_connector_rejects_non_allowlisted_autonomous_operation() -> None:
    executor = ToolExecutor(MockConnector())

    with pytest.raises(ValueError, match="not allowlisted"):
        executor.execute(
            "approve_and_release_withdrawal",
            "CASE-UNSAFE-1",
            idempotency_key=f"test-unsafe-operation-{uuid4().hex}",
        )


def test_incident_threshold_requires_six_unique_customers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lifecycle_module, "_INCIDENT_EVENTS", [])
    monkeypatch.setattr(lifecycle_module, "_INCIDENT_SEEDED", False)
    monkeypatch.setattr(lifecycle_module, "load_cx_context", lambda: {"incident_seed": []})
    detector = EmergingIncidentDetector()
    fifth = None
    for index in range(1, 6):
        fifth = detector.observe(
            customer_id=f"THRESHOLD-C{index}",
            case_id=f"THRESHOLD-CASE-{index}",
            issue_type="withdrawal_processed_missing",
        )
    assert fifth is not None
    assert fifth.unique_customers == 5
    assert fifth.detected is False
    assert fifth.incident_id is None

    sixth = detector.observe(
        customer_id="THRESHOLD-C6",
        case_id="THRESHOLD-CASE-6",
        issue_type="withdrawal_processed_missing",
    )
    duplicate = detector.observe(
        customer_id="THRESHOLD-C6",
        case_id="THRESHOLD-CASE-6",
        issue_type="withdrawal_processed_missing",
    )

    assert sixth.unique_customers == 6
    assert sixth.detected is True
    assert sixth.recommended_action == "notify_incident_manager"
    assert duplicate.unique_customers == 6
    assert duplicate.incident_id == sixth.incident_id


def test_property_graph_maps_sarvagun_and_superturiya_lifecycle() -> None:
    result = AgentRunner().run(_cx_request())
    graph = build_trajectory_property_graph(result)
    labels = {label for node in graph["nodes"] for label in node["labels"]}
    edge_types = {edge["type"] for edge in graph["edges"]}

    assert {"Customer", "Conversation", "ToolExecution", "Transcript", "Escalation", "IncidentCluster", "SuperTuriya", "IntelligenceMemory"}.issubset(labels)
    assert {"EXECUTES_CONVERSATION", "EXECUTES_TOOL", "OBSERVES_AND_EVALUATES", "CREATES_MEMORY"}.issubset(edge_types)


def test_explicit_csat_remains_separate_from_prediction() -> None:
    runner = get_agent_runner()
    result = runner.run(_cx_request())
    assert result.sarvagun is not None
    prediction = result.sarvagun.satisfaction.predicted_satisfaction
    predicted_label = result.sarvagun.satisfaction.predicted_label
    assert result.sarvagun.satisfaction.explicit_csat is None
    assert result.sarvagun.satisfaction.explicit_resolution is None

    response = client.post(
        "/cx/feedback",
        json={"run_id": result.run_id, "explicit_csat": 2, "explicit_resolution": "partially"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_satisfaction"] == prediction
    assert payload["explicit_csat"] == 2
    assert payload["metrics_are_separate"] is True
    persisted = runner.get_run(result.run_id)
    assert persisted is not None and persisted.sarvagun is not None
    assert persisted.sarvagun.satisfaction.predicted_satisfaction == prediction
    assert persisted.sarvagun.satisfaction.predicted_label == predicted_label
    assert persisted.sarvagun.satisfaction.explicit_csat == 2
    assert persisted.sarvagun.satisfaction.explicit_resolution == "partially"
