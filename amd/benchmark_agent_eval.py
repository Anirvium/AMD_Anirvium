#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Anirvium AI support-agent trajectory evaluation.")
    parser.add_argument("--mode", choices=["mock", "llm"], default="mock")
    parser.add_argument("--tickets", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--dataset", choices=["enterprise_saas", "customer_support"], default="customer_support")
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def configure_provider(mode: str) -> None:
    if mode == "llm":
        os.environ["LLM_PROVIDER"] = "openai_compatible"
        os.environ.setdefault("LLM_BASE_URL", "http://localhost:8001/v1")
        os.environ.setdefault("LLM_API_KEY", "dummy")
    else:
        os.environ["LLM_PROVIDER"] = "mock"


def run_once(ticket_count: int, dataset: str) -> Dict[str, Any]:
    from app.schemas.run import RunRequest
    from app.services.agent_runner import AgentRunner
    from app.services.data_loader import load_tickets

    all_tickets = load_tickets(dataset)
    if ticket_count >= len(all_tickets):
        request = RunRequest(selection_mode="all", dataset=dataset)
    else:
        selected_ids = [ticket.ticket_id for ticket in all_tickets[:ticket_count]]
        request = RunRequest(selection_mode="selected", selected_ticket_ids=selected_ids, dataset=dataset)

    runner = AgentRunner()
    start = time.perf_counter()
    result = runner.run(request)
    elapsed_seconds = max(time.perf_counter() - start, 0.001)
    total_tokens = sum(span.tokens_in + span.tokens_out for span in result.trajectory)
    total_latency_ms = sum(span.latency_ms for span in result.trajectory)

    return {
        "run_id": result.run_id,
        "elapsed_seconds": round(elapsed_seconds, 4),
        "tokens_per_second": round(total_tokens / elapsed_seconds, 2),
        "total_tokens": total_tokens,
        "total_latency_ms": total_latency_ms,
        "ticket_count": len(result.selected_ticket_ids),
        "dataset": dataset,
        "agent_step_count": len(result.trajectory),
        "average_step_latency_ms": round(total_latency_ms / max(1, len(result.trajectory)), 2),
        "trajectory_score": result.evaluation.metrics.overall_score,
        "policy_compliance": result.evaluation.metrics.policy_compliance,
        "evidence_grounding": result.evaluation.metrics.evidence_grounding,
        "token_efficiency": result.evaluation.metrics.token_efficiency,
    }


def summarize(mode: str, repeats: int, dataset: str, measurements: List[Dict[str, Any]]) -> Dict[str, Any]:
    tokens_per_second = [item["tokens_per_second"] for item in measurements]
    elapsed = [item["elapsed_seconds"] for item in measurements]
    scores = [item["trajectory_score"] for item in measurements]
    step_latencies = [item["average_step_latency_ms"] for item in measurements]

    return {
        "benchmark_name": "anirvium-agent-trajectory-eval",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "dataset": dataset,
        "provider": "AMD Developer Cloud" if mode == "llm" else "local mock",
        "backend": "vLLM/ROCm" if mode == "llm" else "deterministic mock",
        "llm_base_url": os.getenv("LLM_BASE_URL", ""),
        "llm_model": os.getenv("LLM_MODEL", "mock-trajectory-model"),
        "repeats": repeats,
        "ticket_count": measurements[0]["ticket_count"] if measurements else 0,
        "agent_step_count": measurements[0]["agent_step_count"] if measurements else 0,
        "tokens_per_second_avg": round(statistics.mean(tokens_per_second), 2),
        "tokens_per_second_max": round(max(tokens_per_second), 2),
        "latency_seconds_avg": round(statistics.mean(elapsed), 4),
        "average_step_latency_ms": round(statistics.mean(step_latencies), 2),
        "average_trajectory_score": round(statistics.mean(scores), 2),
        "measurements": measurements,
    }


def main() -> None:
    args = parse_args()
    configure_provider(args.mode)
    measurements = [run_once(args.tickets, args.dataset) for _ in range(args.repeats)]
    report = summarize(args.mode, args.repeats, args.dataset, measurements)

    output = args.output
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        output = ROOT_DIR / "amd" / "logs" / f"benchmark_{args.mode}_{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"Saved benchmark log to {output}")


if __name__ == "__main__":
    main()
