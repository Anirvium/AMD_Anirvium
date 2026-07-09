from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_demo import router as demo_router
from app.api.routes_evaluations import router as evaluations_router
from app.api.routes_kb import router as kb_router
from app.api.routes_memory import router as memory_router
from app.api.routes_runs import router as runs_router
from app.api.routes_tickets import router as tickets_router
from app.config import get_settings


settings = get_settings()

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
