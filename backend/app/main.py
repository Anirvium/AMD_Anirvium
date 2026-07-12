import logging
import time
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request

from app.api.routes_demo import router as demo_router
from app.api.routes_cx import router as cx_router
from app.api.routes_data import router as data_router
from app.api.routes_evaluations import router as evaluations_router
from app.api.routes_kb import router as kb_router
from app.api.routes_memory import router as memory_router
from app.api.routes_platform import router as platform_router
from app.api.routes_runs import router as runs_router
from app.api.routes_tickets import router as tickets_router
from app.config import get_settings
from app.services.observability import bind_observability_context


settings = get_settings()
logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Anirvium AI API",
    description="Anirvium AI APIs for Sarvagun customer-support execution and SuperTuriya trajectory intelligence.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex[:12]
    correlation_id = request.headers.get("x-correlation-id") or request_id
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    bind_observability_context(request_id=request_id, correlation_id=correlation_id)
    started_at = time.perf_counter()
    logger.info(
        "request_started id=%s correlation_id=%s method=%s path=%s",
        request_id,
        correlation_id,
        request.method,
        request.url.path,
    )
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "request_failed id=%s correlation_id=%s method=%s path=%s duration_ms=%s",
            request_id,
            correlation_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-MS"] = str(elapsed_ms)
    logger.info(
        "request_completed id=%s correlation_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        correlation_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "anirvium-ai",
        "mode": settings.llm_provider,
        "synthetic_data_only": True,
        "systems": {"execution": "Sarvagun", "intelligence": "SuperTuriya"},
    }


@app.get("/health/ready")
def readiness() -> dict:
    if settings.llm_provider.lower() not in {"openai", "openai_compatible", "llm"}:
        return {
            "status": "ready",
            "backend_ready": True,
            "model_ready": True,
            "provider": settings.llm_provider,
            "model_id": settings.llm_model,
            "runtime": "deterministic_local",
            "systems": {"execution": "Sarvagun", "intelligence": "SuperTuriya"},
        }
    try:
        response = httpx.get(f"{settings.llm_base_url.rstrip('/')}/models", timeout=3)
        response.raise_for_status()
        model_ids = [item.get("id") for item in response.json().get("data", [])]
        model_ready = settings.llm_model in model_ids
    except (httpx.HTTPError, ValueError, KeyError):
        model_ids = []
        model_ready = False
    return {
        "status": "ready" if model_ready else "degraded",
        "backend_ready": True,
        "model_ready": model_ready,
        "provider": settings.llm_provider,
        "model_id": settings.llm_model,
        "available_models": model_ids,
        "runtime": settings.amd_backend_name,
        "systems": {"execution": "Sarvagun", "intelligence": "SuperTuriya"},
    }


app.include_router(tickets_router)
app.include_router(demo_router)
app.include_router(runs_router)
app.include_router(evaluations_router)
app.include_router(kb_router)
app.include_router(memory_router)
app.include_router(cx_router)
app.include_router(platform_router)
app.include_router(data_router)
