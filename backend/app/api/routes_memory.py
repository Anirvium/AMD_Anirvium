from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.memory import (
    add_long_term_memory,
    get_mid_term_memory,
    get_short_term_memory,
    memory_status,
    search_long_term_memory,
)


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/status")
def get_memory_status() -> dict:
    return memory_status()


@router.get("/short-term/{session_id}")
def get_short_term(session_id: str, limit: int = Query(12, ge=1, le=50)) -> dict:
    records = get_short_term_memory(session_id, limit=limit)
    return {"session_id": session_id, "count": len(records), "records": records}


@router.get("/mid-term/{session_id}")
def get_mid_term(session_id: str, limit: int = Query(10, ge=1, le=50)) -> dict:
    records = get_mid_term_memory(session_id, limit=limit)
    return {"session_id": session_id, "count": len(records), "records": records}


@router.get("/long-term/search")
def search_long_term(q: str = Query(..., min_length=2), limit: int = Query(8, ge=1, le=25)) -> dict:
    records = search_long_term_memory(q, limit=limit)
    return {"query": q, "count": len(records), "records": records}


@router.post("/long-term")
def create_long_term_memory(payload: dict) -> dict:
    memory_id = str(payload.get("id") or payload.get("memory_id") or "LTM-manual")
    text = str(payload.get("text") or payload.get("content") or "")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    record = add_long_term_memory(memory_id, text, metadata=metadata)
    return {"record": record}
