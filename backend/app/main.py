import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request

from app.api.routes_demo import router as demo_router
from app.api.routes_evaluations import router as evaluations_router
from app.api.routes_kb import router as kb_router
from app.api.routes_memory import router as memory_router
from app.api.routes_runs import router as runs_router
from app.api.routes_tickets import router as tickets_router
from app.config import get_settings


settings = get_settings()
logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Anirvium AI API",
    description="Trajectory intelligence APIs for enterprise support-agent workflows.",
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
    started_at = time.perf_counter()
    logger.info("request_started id=%s method=%s path=%s", request_id, request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "request_failed id=%s method=%s path=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = str(elapsed_ms)
    logger.info(
        "request_completed id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
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
    }


app.include_router(tickets_router)
app.include_router(demo_router)
app.include_router(runs_router)
app.include_router(evaluations_router)
app.include_router(kb_router)
app.include_router(memory_router)
