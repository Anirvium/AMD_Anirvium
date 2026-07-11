from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.knowledge_base import kb_layer_summary, load_kb_layer, search_kb_records
from app.services.vector_store import hybrid_kb_search, reindex_kb_vectors, vector_status


router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.get("/layers")
def get_kb_layers() -> dict:
    return kb_layer_summary()


@router.get("/layers/{layer}")
def get_kb_layer(layer: str) -> dict:
    try:
        records = load_kb_layer(layer)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"layer": layer, "count": len(records), "records": records}


@router.get("/search")
def search_kb(
    q: str = Query(..., min_length=2),
    limit: int = Query(8, ge=1, le=25),
    generation_only: bool = False,
    hybrid: bool = True,
) -> dict:
    lexical_records = search_kb_records(q, limit=limit, generation_only=generation_only)
    records = hybrid_kb_search(q, lexical_records, limit=limit, generation_only=generation_only) if hybrid else lexical_records
    return {"query": q, "count": len(records), "hybrid": hybrid, "records": records}


@router.get("/vector/status")
def get_vector_status() -> dict:
    return vector_status()


@router.post("/vector/reindex")
def reindex_vectors() -> dict:
    return reindex_kb_vectors()
