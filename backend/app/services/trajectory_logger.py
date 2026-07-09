import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.trajectory import ApprovalState, TrajectoryGraph, TrajectoryGraphEdge, TrajectoryGraphNode, TrajectorySpan
from app.services.llm_client import estimate_tokens


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


class TrajectoryLogger:
    def __init__(self, store_dir: Path, model_name: str) -> None:
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name

    def create_span(
        self,
        *,
        run_id: str,
        step_index: int,
        parent_step_id: Optional[str],
        agent_name: str,
        input_summary: str,
        full_output: Dict[str, Any],
        latency_ms: int,
    ) -> TrajectorySpan:
        step_id = f"step_{step_index:03d}"
        evidence_ids = sorted(set(full_output.get("evidence_ids", [])))
        risk_flags = sorted(set(full_output.get("risk_flags", [])))
        approval_state = ApprovalState(full_output.get("approval_state", ApprovalState.DRAFT_RECOMMENDATION.value))
        return TrajectorySpan(
            run_id=run_id,
            step_id=step_id,
            parent_step_id=parent_step_id,
            agent_name=agent_name,
            input_summary=input_summary,
            output_summary=full_output.get("summary", f"{agent_name} completed."),
            full_output=full_output,
            tools_used=full_output.get("tools_used", []),
            evidence_ids=evidence_ids,
            latency_ms=latency_ms,
            tokens_in=estimate_tokens(input_summary),
            tokens_out=estimate_tokens(full_output),
            model_name=full_output.get("model_name", self.model_name),
            confidence=float(full_output.get("confidence", 0.82)),
            risk_flags=risk_flags,
            approval_state=approval_state,
        )

    def build_graph(self, spans: List[TrajectorySpan]) -> TrajectoryGraph:
        nodes = []
        edges = []
        for span in spans:
            status = "warning" if span.risk_flags else "success"
            if span.confidence < 0.72:
                status = "review"
            nodes.append(
                TrajectoryGraphNode(
                    id=span.step_id,
                    label=span.agent_name,
                    status=status,
                    score=span.confidence,
                    risk_flags=span.risk_flags,
                )
            )
            if span.parent_step_id:
                edges.append(
                    TrajectoryGraphEdge(
                        source=span.parent_step_id,
                        target=span.step_id,
                        label="passes structured context",
                    )
                )
        return TrajectoryGraph(nodes=nodes, edges=edges)

    def save_run(self, run_id: str, payload: Dict[str, Any]) -> Path:
        path = self.store_dir / f"{run_id}.json"
        with path.open("w", encoding="utf-8") as file:
            json.dump(_jsonable(payload), file, indent=2)
        return path

    def load_run(self, run_id: str) -> Dict[str, Any] | None:
        path = self.store_dir / f"{run_id}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
