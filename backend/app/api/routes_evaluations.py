from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.evaluation import EvaluationReport
from app.services.runtime import get_agent_runner


router = APIRouter(tags=["evaluations"])


@router.get("/runs/latest/evaluation", response_model=EvaluationReport)
def get_latest_evaluation() -> EvaluationReport:
    runner = get_agent_runner()
    result = runner.get_latest_run()
    if result is None:
        raise HTTPException(status_code=404, detail="No runs have been created yet")
    return result.evaluation


@router.get("/runs/{run_id}/evaluation", response_model=EvaluationReport)
def get_evaluation(run_id: str) -> EvaluationReport:
    runner = get_agent_runner()
    result = runner.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result.evaluation


@router.get("/benchmarks/amd")
def get_amd_benchmarks() -> dict:
    settings = get_settings()
    return {
        "provider": settings.amd_provider_name,
        "backend": settings.amd_backend_name,
        "gpu": settings.amd_gpu_name,
        "model": settings.llm_model,
        "runtime_profile": settings.amd_runtime_profile,
        "selected_model_stack": {
            "text_agent": settings.llm_text_model,
            "critic_agent": settings.llm_critic_model,
            "embedding": settings.llm_embedding_model,
            "reranker": settings.llm_reranker_model,
            "safety_model": "deferred",
            "image_video_model": "deferred_text_first",
        },
        "mode": "sample_until_real_amd_log_attached",
        "status": "AMD execution pending",
        "real_evidence_available": False,
        "tokens_per_second": 1180.4,
        "p50_latency_ms": 842,
        "p95_latency_ms": 1310,
        "batch_evaluation_throughput": "8 tickets / 7 agent steps / 3.4s sample mock replay",
        "average_trajectory_score": 87.6,
        "benchmark_log_path": "amd/logs/benchmark_sample.json",
        "future_real_evidence_paths": [
            "amd/logs/benchmark_amd_real_<date>.json",
            "amd/benchmark_results_real.md",
            "amd/screenshots/vllm_running.png",
            "amd/screenshots/benchmark_output.png",
            "amd/screenshots/dashboard_amd_panel.png",
        ],
        "notes": [
            "Real AMD benchmark pending. Scripts and runbook are prepared.",
            "Sample files are marked as sample and are not claimed as verified AMD execution.",
            "Run amd/benchmark_agent_eval.py on AMD Developer Cloud with vLLM/ROCm to replace sample values.",
            "The app records tokens/sec, latency, throughput, ticket count, agent-step count, and trajectory score.",
            "Runtime strategy: run text inference first; image/video model loading is deferred until text trajectory benchmark is verified.",
            "Llama Guard is intentionally deferred; deterministic policy gates and approval states are active now.",
        ],
    }
