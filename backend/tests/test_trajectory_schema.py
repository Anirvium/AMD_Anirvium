from app.schemas.trajectory import ApprovalState, TrajectorySpan


def test_trajectory_span_contains_required_observability_fields() -> None:
    span = TrajectorySpan(
        run_id="run_test",
        step_id="step_001",
        agent_name="Policy Checker Agent",
        input_summary="Check policies.",
        output_summary="Approval required.",
        full_output={"summary": "Approval required."},
        tools_used=["policy_rules_engine"],
        evidence_ids=["POL-001"],
        latency_ms=12,
        tokens_in=20,
        tokens_out=40,
        model_name="mock-trajectory-model",
        confidence=0.88,
        risk_flags=["REFUND_APPROVAL_REQUIRED"],
        approval_state=ApprovalState.APPROVAL_REQUIRED,
    )

    assert span.run_id == "run_test"
    assert span.approval_state == ApprovalState.APPROVAL_REQUIRED
    assert span.evidence_ids == ["POL-001"]
    assert span.risk_flags == ["REFUND_APPROVAL_REQUIRED"]

