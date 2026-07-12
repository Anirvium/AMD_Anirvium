from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class PathSignature(BaseModel):
    step_sequence: List[str] = Field(default_factory=list)
    edge_sequence: List[str] = Field(default_factory=list)
    sha256: str
    span_count: int = Field(ge=0)
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)


class StringSetDelta(BaseModel):
    shared: List[str] = Field(default_factory=list)
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)


class NumericDelta(BaseModel):
    baseline: float
    candidate: float
    delta: float


class MetricDelta(NumericDelta):
    direction: Literal["increased", "decreased", "unchanged"]
    impact: Literal["improved", "regressed", "unchanged"]
    higher_is_better: bool


class OperationalComparison(BaseModel):
    total_latency_ms: NumericDelta
    tokens_in: NumericDelta
    tokens_out: NumericDelta
    total_tokens: NumericDelta
    recorded_tool_calls: NumericDelta
    unique_tools: NumericDelta
    enterprise_tool_executions: NumericDelta
    evidence_references: NumericDelta
    unique_evidence: NumericDelta
    tools: StringSetDelta
    evidence: StringSetDelta


class ComparisonVerdict(BaseModel):
    outcome: Literal["candidate_improved", "candidate_regressed", "mixed", "equivalent"]
    summary: str
    reasons: List[str] = Field(default_factory=list)
    methodology: str


class RunComparisonResponse(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    baseline_path: PathSignature
    candidate_path: PathSignature
    path_changed: bool
    steps: StringSetDelta
    edges: StringSetDelta
    metrics: Dict[str, MetricDelta]
    overall_score: NumericDelta
    operations: OperationalComparison
    failures: StringSetDelta
    risks: StringSetDelta
    verdict: ComparisonVerdict
