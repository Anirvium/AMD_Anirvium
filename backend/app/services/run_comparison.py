from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Dict, List, Sequence

from app.schemas.comparison import (
    ComparisonVerdict,
    MetricDelta,
    NumericDelta,
    OperationalComparison,
    PathSignature,
    RunComparisonResponse,
    StringSetDelta,
)
from app.schemas.run import RunResult


_EPSILON = 1e-9
_LOWER_IS_BETTER = {"hallucination_risk", "missing_information"}
_SAFETY_METRICS = {"task_completion", "evidence_grounding", "policy_compliance", "hallucination_risk"}


def compare_run_results(baseline: RunResult, candidate: RunResult) -> RunComparisonResponse:
    baseline_path = _path_signature(baseline)
    candidate_path = _path_signature(candidate)
    steps = _sequence_delta(baseline_path.step_sequence, candidate_path.step_sequence)
    edges = _sequence_delta(baseline_path.edge_sequence, candidate_path.edge_sequence)
    metrics = _metric_deltas(baseline, candidate)
    overall_score = _numeric_delta(
        baseline.evaluation.metrics.overall_score,
        candidate.evaluation.metrics.overall_score,
    )
    operations = _operational_comparison(baseline, candidate)
    failures = _sequence_delta(_failure_signatures(baseline), _failure_signatures(candidate))
    risks = _sequence_delta(_risk_signatures(baseline), _risk_signatures(candidate))
    verdict = _verdict(
        metrics=metrics,
        overall_score=overall_score,
        failures=failures,
        risks=risks,
        path_changed=baseline_path.sha256 != candidate_path.sha256,
    )
    return RunComparisonResponse(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        path_changed=baseline_path.sha256 != candidate_path.sha256,
        steps=steps,
        edges=edges,
        metrics=metrics,
        overall_score=overall_score,
        operations=operations,
        failures=failures,
        risks=risks,
        verdict=verdict,
    )


def _path_signature(run: RunResult) -> PathSignature:
    occurrence_counts: Counter[str] = Counter()
    node_identity: Dict[str, str] = {}
    step_sequence: List[str] = []

    for span in run.trajectory:
        occurrence_counts[span.agent_name] += 1
        identity = f"{span.agent_name}#{occurrence_counts[span.agent_name]}"
        node_identity[span.step_id] = identity
        step_sequence.append(identity)

    for node in run.graph.nodes:
        if node.id in node_identity:
            continue
        occurrence_counts[node.label] += 1
        identity = f"{node.label}#{occurrence_counts[node.label]}"
        node_identity[node.id] = identity
        step_sequence.append(identity)

    edge_sequence = [
        _edge_identity(
            node_identity.get(edge.source, f"unmapped:{edge.source}"),
            node_identity.get(edge.target, f"unmapped:{edge.target}"),
            edge.label,
        )
        for edge in run.graph.edges
    ]
    signature_payload = json.dumps(
        {"steps": step_sequence, "edges": edge_sequence},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return PathSignature(
        step_sequence=step_sequence,
        edge_sequence=edge_sequence,
        sha256=hashlib.sha256(signature_payload).hexdigest(),
        span_count=len(run.trajectory),
        node_count=len(run.graph.nodes),
        edge_count=len(run.graph.edges),
    )


def _edge_identity(source: str, target: str, label: str) -> str:
    return f"{source} -> {target} [{label}]"


def _sequence_delta(baseline: Sequence[str], candidate: Sequence[str]) -> StringSetDelta:
    baseline_unique = list(dict.fromkeys(baseline))
    candidate_unique = list(dict.fromkeys(candidate))
    baseline_set = set(baseline_unique)
    candidate_set = set(candidate_unique)
    return StringSetDelta(
        shared=[item for item in baseline_unique if item in candidate_set],
        added=[item for item in candidate_unique if item not in baseline_set],
        removed=[item for item in baseline_unique if item not in candidate_set],
    )


def _metric_deltas(baseline: RunResult, candidate: RunResult) -> Dict[str, MetricDelta]:
    baseline_metrics = baseline.evaluation.metrics.model_dump()
    candidate_metrics = candidate.evaluation.metrics.model_dump()
    deltas: Dict[str, MetricDelta] = {}
    for metric_name, baseline_value in baseline_metrics.items():
        candidate_value = float(candidate_metrics[metric_name])
        baseline_number = float(baseline_value)
        delta = _clean_delta(candidate_value - baseline_number)
        higher_is_better = metric_name not in _LOWER_IS_BETTER
        direction = "unchanged" if delta == 0 else "increased" if delta > 0 else "decreased"
        if delta == 0:
            impact = "unchanged"
        elif (delta > 0) == higher_is_better:
            impact = "improved"
        else:
            impact = "regressed"
        deltas[metric_name] = MetricDelta(
            baseline=baseline_number,
            candidate=candidate_value,
            delta=delta,
            direction=direction,
            impact=impact,
            higher_is_better=higher_is_better,
        )
    return deltas


def _operational_comparison(baseline: RunResult, candidate: RunResult) -> OperationalComparison:
    baseline_tools = [tool for span in baseline.trajectory for tool in span.tools_used]
    candidate_tools = [tool for span in candidate.trajectory for tool in span.tools_used]
    baseline_evidence = [item for span in baseline.trajectory for item in span.evidence_ids]
    candidate_evidence = [item for span in candidate.trajectory for item in span.evidence_ids]
    baseline_enterprise_tools = len(baseline.sarvagun.tool_executions) if baseline.sarvagun else 0
    candidate_enterprise_tools = len(candidate.sarvagun.tool_executions) if candidate.sarvagun else 0

    baseline_tokens_in = sum(span.tokens_in for span in baseline.trajectory)
    candidate_tokens_in = sum(span.tokens_in for span in candidate.trajectory)
    baseline_tokens_out = sum(span.tokens_out for span in baseline.trajectory)
    candidate_tokens_out = sum(span.tokens_out for span in candidate.trajectory)
    return OperationalComparison(
        total_latency_ms=_numeric_delta(
            sum(span.latency_ms for span in baseline.trajectory),
            sum(span.latency_ms for span in candidate.trajectory),
        ),
        tokens_in=_numeric_delta(baseline_tokens_in, candidate_tokens_in),
        tokens_out=_numeric_delta(baseline_tokens_out, candidate_tokens_out),
        total_tokens=_numeric_delta(
            baseline_tokens_in + baseline_tokens_out,
            candidate_tokens_in + candidate_tokens_out,
        ),
        recorded_tool_calls=_numeric_delta(len(baseline_tools), len(candidate_tools)),
        unique_tools=_numeric_delta(len(set(baseline_tools)), len(set(candidate_tools))),
        enterprise_tool_executions=_numeric_delta(baseline_enterprise_tools, candidate_enterprise_tools),
        evidence_references=_numeric_delta(len(baseline_evidence), len(candidate_evidence)),
        unique_evidence=_numeric_delta(len(set(baseline_evidence)), len(set(candidate_evidence))),
        tools=_sequence_delta(baseline_tools, candidate_tools),
        evidence=_sequence_delta(baseline_evidence, candidate_evidence),
    )


def _failure_signatures(run: RunResult) -> List[str]:
    return list(
        dict.fromkeys(
            f"{(item.failure_type or item.category).upper()} [{item.severity.upper()}]"
            for item in run.evaluation.diagnosis
        )
    )


def _risk_signatures(run: RunResult) -> List[str]:
    flags: List[str] = []
    for span in run.trajectory:
        flags.extend(span.risk_flags)
    for action in run.final_actions:
        flags.extend(action.risk_flags)
    return list(dict.fromkeys(flags))


def _verdict(
    *,
    metrics: Dict[str, MetricDelta],
    overall_score: NumericDelta,
    failures: StringSetDelta,
    risks: StringSetDelta,
    path_changed: bool,
) -> ComparisonVerdict:
    metric_improvements = sorted(name for name, delta in metrics.items() if delta.impact == "improved" and name != "overall_score")
    metric_regressions = sorted(name for name, delta in metrics.items() if delta.impact == "regressed" and name != "overall_score")
    safety_regressions = sorted(name for name in metric_regressions if name in _SAFETY_METRICS)
    added_high_severity_failures = sorted(
        failure for failure in failures.added if failure.endswith("[HIGH]") or failure.endswith("[CRITICAL]")
    )

    reasons = [f"Overall trajectory score delta: {overall_score.delta:+.3f}."]
    if metric_improvements:
        reasons.append(f"Improved metrics: {', '.join(metric_improvements)}.")
    if metric_regressions:
        reasons.append(f"Regressed metrics: {', '.join(metric_regressions)}.")
    if failures.added:
        reasons.append(f"Added evaluated failures: {', '.join(failures.added)}.")
    if added_high_severity_failures:
        reasons.append(f"New high-severity failures: {', '.join(added_high_severity_failures)}.")
    if failures.removed:
        reasons.append(f"Removed evaluated failures: {', '.join(failures.removed)}.")
    if risks.added or risks.removed:
        reasons.append(f"Risk flags changed: +{len(risks.added)} / -{len(risks.removed)}.")
    reasons.append("The stored execution path changed." if path_changed else "The stored execution path is unchanged.")

    if safety_regressions or added_high_severity_failures:
        outcome = "candidate_regressed"
        summary = "The candidate has a measured safety or high-severity failure regression."
    elif overall_score.delta > _EPSILON:
        outcome = "candidate_improved"
        summary = "The candidate improved the recorded overall trajectory score without a critical safety regression."
    elif overall_score.delta < -_EPSILON:
        outcome = "candidate_regressed"
        summary = "The candidate reduced the recorded overall trajectory score."
    elif metric_improvements and metric_regressions:
        outcome = "mixed"
        summary = "The overall score is unchanged while component metrics moved in both directions."
    elif metric_improvements:
        outcome = "candidate_improved"
        summary = "The overall score is unchanged, but one or more component metrics improved."
    elif metric_regressions:
        outcome = "candidate_regressed"
        summary = "The overall score is unchanged, but one or more component metrics regressed."
    elif failures.added and failures.removed:
        outcome = "mixed"
        summary = "The overall score and component metrics are unchanged, but evaluated failure types changed."
    elif failures.added:
        outcome = "candidate_regressed"
        summary = "The candidate added an evaluated failure while recorded metric scores remained unchanged."
    elif failures.removed:
        outcome = "candidate_improved"
        summary = "The candidate removed an evaluated failure while recorded metric scores remained unchanged."
    else:
        outcome = "equivalent"
        summary = "No measured evaluation-quality difference was found between the stored runs."

    return ComparisonVerdict(
        outcome=outcome,
        summary=summary,
        reasons=reasons,
        methodology=(
            "Deterministic comparison of persisted trajectory graphs, spans, evaluation metrics, diagnoses, "
            "risk flags, and recorded operational counts. Any task-completion, evidence-grounding, policy-compliance, "
            "or hallucination-risk regression, or any newly added HIGH/CRITICAL diagnosis, overrides a higher overall score. "
            "Risk flags and operational deltas are reported but do not independently determine quality because they may reflect better detection or different workload."
        ),
    )


def _numeric_delta(baseline: float | int, candidate: float | int) -> NumericDelta:
    baseline_number = float(baseline)
    candidate_number = float(candidate)
    return NumericDelta(
        baseline=baseline_number,
        candidate=candidate_number,
        delta=_clean_delta(candidate_number - baseline_number),
    )


def _clean_delta(value: float) -> float:
    if abs(value) <= _EPSILON:
        return 0.0
    return round(value, 6)
