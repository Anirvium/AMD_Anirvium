from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.config import get_settings
from app.services.vector_store import upsert_vector_records, vector_search


_SHORT_TERM_LOCAL: Dict[str, List[Dict[str, Any]]] = {}
_MID_TERM_LOCAL: Dict[str, List[Dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redis_command(*parts: str) -> Any:
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = (parsed.path or "/0").strip("/") or "0"
    payload = b"".join(
        [
            f"*{len(parts) + 1}\r\n".encode("utf-8"),
            b"$6\r\nSELECT\r\n",
            f"${len(db)}\r\n{db}\r\n".encode("utf-8"),
        ]
    )
    command = b"".join([f"*{len(parts)}\r\n".encode("utf-8")] + [f"${len(part)}\r\n{part}\r\n".encode("utf-8") for part in parts])
    with socket.create_connection((host, port), timeout=2) as connection:
        connection.sendall(payload)
        connection.recv(1024)
        connection.sendall(command)
        return connection.recv(65536)


def _redis_available() -> bool:
    if get_settings().memory_backend != "redis":
        return False
    try:
        _redis_command("PING")
        return True
    except OSError:
        return False


def add_short_term_memory(session_id: str, content: str, *, role: str = "system", metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    record = {
        "id": f"STM-{session_id}-{len(_SHORT_TERM_LOCAL.get(session_id, [])) + 1:04d}",
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "created_at": _now(),
    }
    settings = get_settings()
    if _redis_available():
        key = f"anirvium:stm:{session_id}"
        encoded = json.dumps(record)
        _redis_command("LPUSH", key, encoded)
        _redis_command("LTRIM", key, "0", str(settings.mid_term_memory_limit - 1))
        _redis_command("EXPIRE", key, str(settings.short_term_memory_ttl_seconds))
    _SHORT_TERM_LOCAL.setdefault(session_id, []).insert(0, record)
    _SHORT_TERM_LOCAL[session_id] = _SHORT_TERM_LOCAL[session_id][: settings.mid_term_memory_limit]
    return record


def get_short_term_memory(session_id: str, *, limit: int = 12) -> List[Dict[str, Any]]:
    if _redis_available():
        # Local mirror is intentionally still used for deterministic tests.
        pass
    return _SHORT_TERM_LOCAL.get(session_id, [])[:limit]


def add_mid_term_summary(session_id: str, summary: str, *, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    settings = get_settings()
    record = {
        "id": f"MTM-{session_id}-{len(_MID_TERM_LOCAL.get(session_id, [])) + 1:04d}",
        "session_id": session_id,
        "summary": summary,
        "metadata": metadata or {},
        "created_at": _now(),
    }
    _MID_TERM_LOCAL.setdefault(session_id, []).insert(0, record)
    _MID_TERM_LOCAL[session_id] = _MID_TERM_LOCAL[session_id][: settings.mid_term_memory_limit]
    return record


def get_mid_term_memory(session_id: str, *, limit: int = 10) -> List[Dict[str, Any]]:
    return _MID_TERM_LOCAL.get(session_id, [])[:limit]


def add_long_term_memory(memory_id: str, text: str, *, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    record = {
        "id": memory_id,
        "title": metadata.get("title", memory_id) if metadata else memory_id,
        "text": text,
        "memory_type": metadata.get("memory_type", "long_term") if metadata else "long_term",
        "metadata": metadata or {},
        "created_at": _now(),
    }
    upsert_vector_records([record], kind="memory")
    return record


def search_long_term_memory(query: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    return vector_search(query, limit=limit, kind="memory")


def index_trajectory_memory(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = run_payload["run_id"]
    final_actions = run_payload.get("final_actions", [])
    evaluation = run_payload.get("evaluation", {})
    text = json.dumps(
        {
            "run_id": run_id,
            "selected_ticket_ids": run_payload.get("selected_ticket_ids", []),
            "final_actions": final_actions,
            "evaluation_summary": evaluation.get("summary"),
            "metrics": evaluation.get("metrics"),
            "diagnosis": evaluation.get("diagnosis", []),
            "recommendations": evaluation.get("recommendations", []),
        },
        sort_keys=True,
    )
    trajectory_record = {
        "id": f"TRAJ-{run_id}",
        "title": f"Trajectory memory for {run_id}",
        "text": text,
        "memory_type": "trajectory",
        "run_id": run_id,
        "created_at": _now(),
    }
    result = upsert_vector_records([trajectory_record], kind="trajectory")
    add_long_term_memory(
        f"LTM-{run_id}",
        text,
        metadata={"title": f"Long-term summary for {run_id}", "memory_type": "trajectory_summary", "run_id": run_id},
    )
    return result


def memory_status() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "memory_backend": settings.memory_backend,
        "redis_configured": settings.memory_backend == "redis",
        "redis_reachable": _redis_available(),
        "short_term_sessions": len(_SHORT_TERM_LOCAL),
        "mid_term_sessions": len(_MID_TERM_LOCAL),
        "short_term_ttl_seconds": settings.short_term_memory_ttl_seconds,
        "mid_term_limit": settings.mid_term_memory_limit,
    }
