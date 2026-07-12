from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

from app.config import get_settings
from app.services.knowledge_base import kb_layer_summary
from app.services.memory import memory_status
from app.services.relational_store import relational_status
from app.services.vector_store import vector_status


router = APIRouter(prefix="/platform", tags=["platform-inventory"])


def _model_inventory() -> Dict[str, Any]:
    settings = get_settings()
    live_provider = settings.llm_provider.lower() in {"openai", "openai_compatible", "llm"}
    return {
        "generation": {
            "active": live_provider,
            "model": settings.llm_model if live_provider else "mock-trajectory-model",
            "provider": settings.llm_provider,
            "endpoint": settings.llm_base_url if live_provider else None,
            "role": "Sarvagun response drafting and routed public general knowledge",
        },
        "superturiya_critic": {
            "active": True,
            "model": (
                settings.llm_model
                if settings.llm_auxiliary_reviews and live_provider
                else "deterministic-trajectory-evaluator-v1"
            ),
            "configured_optional_model": settings.llm_critic_model,
            "llm_auxiliary_review_active": settings.llm_auxiliary_reviews and live_provider,
        },
        "embedding": {
            "active": True,
            "model": "deterministic-token-hash-64d",
            "dimension": settings.vector_dimension,
            "configured_optional_model": settings.llm_embedding_model,
            "external_model_active": False,
        },
        "reranking": {
            "active": True,
            "model": "deterministic-hybrid-rank-fusion",
            "configured_optional_model": settings.llm_reranker_model,
            "external_model_active": False,
        },
        "classification_and_guardrails": {
            "active": True,
            "model": "deterministic-rules",
            "external_model_active": False,
        },
    }


def _storage_inventory() -> Dict[str, Any]:
    settings = get_settings()
    vector = vector_status()
    vector["terminology"] = "collections_not_clusters"
    vector["collection_roles"] = {
        settings.vector_kb_collection: {
            "owner": "Sarvagun",
            "role": "curated policy, procedure, template, evidence, and evaluation retrieval",
            "write_policy": "curated_ingestion_and_reindex",
        },
        settings.vector_memory_collection: {
            "owner": "SuperTuriya",
            "role": "long-term semantic memory from evaluated trajectory summaries and transcripts",
            "trusted_recall_scope": "superturiya_evaluated_memory",
        },
        settings.vector_trajectory_collection: {
            "owner": "SuperTuriya",
            "role": "whole-run trajectory documents for similarity search and experience reuse",
            "write_policy": "after_each_completed_evaluated_run",
        },
    }
    return {
        "relational_operational_truth": relational_status(),
        "short_and_mid_term_memory": memory_status(),
        "semantic_vector_retrieval": vector,
        "trajectory_json_store": {
            "backend": "filesystem_json",
            "configured_path": str(Path(settings.run_store_dir)),
            "role": "auditable full-fidelity run fallback and demo persistence",
        },
    }


@router.get("/status")
def platform_status() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "platform": "Anirvium AI",
        "systems": {
            "execution": "Sarvagun",
            "trajectory_intelligence": "SuperTuriya",
        },
        "runtime": {
            "provider": settings.amd_provider_name,
            "inference_backend": settings.amd_backend_name,
            "gpu": settings.amd_gpu_name,
            "profile": settings.amd_runtime_profile,
            "synthetic_data_only": True,
        },
        "routing": {
            "architecture": "hybrid_typed_capability_router",
            "paths": [
                "conversation_fast_path",
                "direct_relational_read",
                "deterministic_analytics",
                "general_knowledge_llm",
                "sarvagun_agent_pipeline",
            ],
            "support_actions_governed": True,
        },
        "agents": {
            "sarvagun": [
                "Planner Agent",
                "Attachment Evidence Agent",
                "Intake / Triage Agent",
                "Knowledge Retrieval Agent",
                "Policy Checker Agent",
                "Escalation Agent",
                "Response Drafting Agent",
                "Compliance Agent",
                "Human Escalation Agent",
            ],
            "superturiya": [
                "Critic / Evaluator Agent",
                "Reflection Agent",
                "Learning Extraction Agent",
                "Optimizer Agent",
            ],
        },
        "models": _model_inventory(),
        "storage": _storage_inventory(),
        "knowledge_base": kb_layer_summary(),
        "external_benchmarks": {
            "tau_bench": {"used": False, "official_score": None},
            "tau2_bench": {"used": False, "official_score": None},
            "tau3_bench": {"used": False, "official_score": None},
            "internal_suite": "sarvagun-curated-eval-v1",
            "claim": "internal_synthetic_evaluation_only",
        },
        "production_boundaries": {
            "connectors": "simulated_and_audited",
            "automatic_policy_mutation": False,
            "human_review_enforced_for_risky_actions": True,
            "durable_multi_worker_job_queue": False,
            "otel_exporter": False,
        },
    }
