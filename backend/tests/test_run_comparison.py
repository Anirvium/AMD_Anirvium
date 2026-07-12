from __future__ import annotations

from typing import Dict, Iterable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_runs
from app.schemas.evaluation import DiagnosisItem, EvaluationMetrics, EvaluationReport
from app.schemas.run import FinalAction, RunResult
from app.schemas.trajectory import (
    ApprovalState,
    TrajectoryGraph,
    TrajectoryGraphEdge,
    TrajectoryGraphNode,
    TrajectorySpan,
)
from app.services.run_comparison import compare_run_results


def _metrics(**overrides: float) -> EvaluationMetrics:
    values = {
        "task_completion": 0.8,
        "evidence_grounding": 0.8,
        "policy_compliance": 0.9,
        "hallucination_risk": 0.2,
        "escalation_quality": 0.8,
        "actionability": 0.8,
        "missing_information": 0.2,
        "customer_tone": 0.8,
        "token_efficiency": 0.7,
        "latency_efficiency": 0.7,
        "overall_score": 75.0,
    }
    values.update(overrides)
    return EvaluationMetrics(**values)


def _run(
    run_id: str,
    *,
    agents: Iterable[str],
    metrics: EvaluationMetrics,
    diagnosis: list[DiagnosisItem] | None = None,
    latency_ms: int = 50,
    tools: Dict[str, list[str]] | None = None,
    evidence: Dict[str, list[str]] | None = None,
    risks: Dict[str, list[str]] | None = None,
) -> RunResult:
    agent_names = list(agents)
    tools = tools or {}
    evidence = evidence or {}
    risks = risks or {}
    spans: list[TrajectorySpan] = []
    nodes: list[TrajectoryGraphNode] = []
    edges: list[TrajectoryGraphEdge] = []
    for index, agent_name in enumerate(agent_names, start=1):
        step_id = f"step_{index:03d}"
        parent_id = f"step_{index - 1:03d}" if index > 1 else None
        step_risks = risks.get(agent_name, [])
        spans.append(
            TrajectorySpan(
                run_id=run_id,
                step_id=step_id,
                parent_step_id=parent_id,
                agent_name=agent_name,
                input_summary=f"Input for {agent_name}",
                output_summary=f"Output from {agent_name}",
                reasoning_summary=f"Decision summary for {agent_name}",
                full_output={"summary": f"Output from {agent_name}"},
                tools_used=tools.get(agent_name, []),
                evidence_ids=evidence.get(agent_name, []),
                latency_ms=latency_ms,
                tokens_in=10,
                tokens_out=20,
                confidence=0.85,
                risk_flags=step_risks,
                approval_state=ApprovalState.DRAFT_RECOMMENDATION,
            )
        )
        nodes.append(
            TrajectoryGraphNode(
                id=step_id,
                label=agent_name,
                status="warning" if step_risks else "success",
                score=0.85,
                risk_flags=step_risks,
            )
        )
        if parent_id:
            edges.append(
                TrajectoryGraphEdge(
                    source=parent_id,
                    target=step_id,
                    label="passes structured context",
                )
            )
    report = EvaluationReport(
        run_id=run_id,
        metrics=metrics,
        diagnosis=diagnosis or [],
        recommendations=[],
        summary=f"Score {metrics.overall_score}",
    )
    action_risks = sorted({risk for values in risks.values() for risk in values})
    return RunResult(
        run_id=run_id,
        status="completed",
        selected_ticket_ids=["CS-001"],
        final_actions=[
            FinalAction(
                ticket_id="CS-001",
                customer_name="Test Customer",
                recommended_escalation="Support operations",
                owner="Support queue",
                urgency="medium",
                approval_state="DRAFT_RECOMMENDATION",
                draft_response="A governed response draft.",
                evidence_ids=sorted({item for values in evidence.values() for item in values}),
                risk_flags=action_risks,
                next_action="Continue support review.",
            )
        ],
        trajectory=spans,
        graph=TrajectoryGraph(nodes=nodes, edges=edges),
        evaluation=report,
    )


def _diagnosis(failure_type: str, severity: str = "HIGH") -> DiagnosisItem:
    return DiagnosisItem(
        category="quality",
        severity=severity,
        message=failure_type,
        suggested_fix="Fix the measured failure.",
        failure_type=failure_type,
        affected_agent="Response Drafting Agent",
        business_impact="Customer support quality",
        recommended_fix="Fix the measured failure.",
        metric_impact=["overall_score"],
    )


def test_comparison_reports_actual_path_metric_and_operational_deltas() -> None:
    baseline = _run(
        "run_baseline",
        agents=["Planner Agent", "Response Drafting Agent"],
        metrics=_metrics(overall_score=70.0, evidence_grounding=0.6, hallucination_risk=0.3),
        diagnosis=[_diagnosis("UNSUPPORTED_RESPONSE")],
        latency_ms=100,
        tools={"Planner Agent": ["plan_router"], "Response Drafting Agent": ["draft_tool"]},
        evidence={"Response Drafting Agent": ["POL-1"]},
        risks={"Response Drafting Agent": ["UNSUPPORTED_PROMISE"]},
    )
    candidate = _run(
        "run_candidate",
        agents=["Planner Agent", "Compliance Agent", "Response Drafting Agent"],
        metrics=_metrics(overall_score=82.0, evidence_grounding=0.95, hallucination_risk=0.05),
        latency_ms=20,
        tools={
            "Planner Agent": ["plan_router"],
            "Compliance Agent": ["policy_gate"],
            "Response Drafting Agent": ["draft_tool"],
        },
        evidence={"Compliance Agent": ["POL-1", "POL-2"]},
    )

    comparison = compare_run_results(baseline, candidate)

    assert comparison.path_changed is True
    assert comparison.steps.added == ["Compliance Agent#1"]
    assert "Planner Agent#1 -> Response Drafting Agent#1 [passes structured context]" in comparison.edges.removed
    assert comparison.metrics["evidence_grounding"].delta == 0.35
    assert comparison.metrics["hallucination_risk"].impact == "improved"
    assert comparison.overall_score.delta == 12.0
    assert comparison.operations.total_latency_ms.delta == -140.0
    assert comparison.operations.recorded_tool_calls.delta == 1.0
    assert comparison.operations.unique_evidence.delta == 1.0
    assert comparison.failures.removed == ["UNSUPPORTED_RESPONSE [HIGH]"]
    assert comparison.risks.removed == ["UNSUPPORTED_PROMISE"]
    assert comparison.verdict.outcome == "candidate_improved"


def test_comparison_safety_regression_overrides_higher_overall_score() -> None:
    baseline = _run(
        "run_safe",
        agents=["Planner Agent", "Policy Checker Agent"],
        metrics=_metrics(overall_score=80.0, policy_compliance=1.0),
    )
    candidate = _run(
        "run_unsafe",
        agents=["Planner Agent", "Policy Checker Agent"],
        metrics=_metrics(overall_score=85.0, policy_compliance=0.6),
    )

    comparison = compare_run_results(baseline, candidate)

    assert comparison.overall_score.delta == 5.0
    assert comparison.metrics["policy_compliance"].impact == "regressed"
    assert comparison.verdict.outcome == "candidate_regressed"
    assert "safety" in comparison.verdict.summary.lower()


def test_comparing_a_run_with_itself_is_equivalent_and_stable() -> None:
    run = _run(
        "run_same",
        agents=["Planner Agent", "Response Drafting Agent"],
        metrics=_metrics(),
        tools={"Planner Agent": ["plan_router"]},
        evidence={"Response Drafting Agent": ["POL-1"]},
    )

    first = compare_run_results(run, run)
    second = compare_run_results(run, run)

    assert first == second
    assert first.baseline_path.sha256 == first.candidate_path.sha256
    assert first.steps.added == []
    assert first.edges.removed == []
    assert all(delta.delta == 0 for delta in first.metrics.values())
    assert first.verdict.outcome == "equivalent"


def test_compare_endpoint_reads_stored_runs_and_reports_missing_ids(monkeypatch) -> None:
    baseline = _run(
        "run_api_baseline",
        agents=["Planner Agent"],
        metrics=_metrics(overall_score=70.0),
    )
    candidate = _run(
        "run_api_candidate",
        agents=["Planner Agent", "Optimizer Agent"],
        metrics=_metrics(overall_score=75.0),
    )

    class FakeRunner:
        def get_run(self, run_id: str) -> RunResult | None:
            return {baseline.run_id: baseline, candidate.run_id: candidate}.get(run_id)

    monkeypatch.setattr(routes_runs, "get_agent_runner", lambda: FakeRunner())
    app = FastAPI()
    app.include_router(routes_runs.router)
    client = TestClient(app)

    response = client.get(
        "/runs/compare",
        params={"baseline_run_id": baseline.run_id, "candidate_run_id": candidate.run_id},
    )
    assert response.status_code == 200
    assert response.json()["verdict"]["outcome"] == "candidate_improved"
    assert response.json()["candidate_path"]["span_count"] == 2

    missing = client.get(
        "/runs/compare",
        params={"baseline_run_id": "missing", "candidate_run_id": candidate.run_id},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Baseline run not found: missing"
