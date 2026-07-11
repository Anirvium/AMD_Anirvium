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


def _encode_redis_command(*parts: str) -> bytes:
    return b"".join(
        [f"*{len(parts)}\r\n".encode("utf-8")]
        + [f"${len(part.encode('utf-8'))}\r\n{part}\r\n".encode("utf-8") for part in parts]
    )


def _parse_redis_response(payload: bytes) -> Any:
    def parse_at(offset: int) -> tuple[Any, int]:
        prefix = payload[offset : offset + 1]
        line_end = payload.find(b"\r\n", offset)
        if line_end < 0:
            raise ValueError("Incomplete Redis response")
        line = payload[offset + 1 : line_end]
        next_offset = line_end + 2
        if prefix == b"+":
            return line.decode("utf-8"), next_offset
        if prefix == b"-":
            raise RuntimeError(line.decode("utf-8"))
        if prefix == b":":
            return int(line), next_offset
        if prefix == b"$":
            length = int(line)
            if length < 0:
                return None, next_offset
            value = payload[next_offset : next_offset + length].decode("utf-8")
            return value, next_offset + length + 2
        if prefix == b"*":
            count = int(line)
            values = []
            for _ in range(max(0, count)):
                value, next_offset = parse_at(next_offset)
                values.append(value)
            return values, next_offset
        raise ValueError("Unsupported Redis response")

    return parse_at(0)[0]


def _redis_command(*parts: str) -> Any:
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = (parsed.path or "/0").strip("/") or "0"
    with socket.create_connection((host, port), timeout=2) as connection:
        if parsed.password:
            auth_parts = ("AUTH", parsed.username, parsed.password) if parsed.username else ("AUTH", parsed.password)
            connection.sendall(_encode_redis_command(*auth_parts))
            _parse_redis_response(connection.recv(4096))
        connection.sendall(_encode_redis_command("SELECT", db))
        _parse_redis_response(connection.recv(4096))
        connection.sendall(_encode_redis_command(*parts))
        return _parse_redis_response(connection.recv(65536))


def _redis_available() -> bool:
    if get_settings().memory_backend != "redis":
        return False
    try:
        _redis_command("PING")
        return True
    except (OSError, RuntimeError, ValueError):
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
        key = f"anirvium:sarvagun:session:{session_id}"
        encoded = json.dumps(record)
        try:
            _redis_command("LPUSH", key, encoded)
            _redis_command("LTRIM", key, "0", str(settings.mid_term_memory_limit - 1))
            _redis_command("EXPIRE", key, str(settings.short_term_memory_ttl_seconds))
        except (OSError, RuntimeError, ValueError):
            pass
    _SHORT_TERM_LOCAL.setdefault(session_id, []).insert(0, record)
    _SHORT_TERM_LOCAL[session_id] = _SHORT_TERM_LOCAL[session_id][: settings.mid_term_memory_limit]
    return record


def get_short_term_memory(session_id: str, *, limit: int = 12) -> List[Dict[str, Any]]:
    if _redis_available():
        key = f"anirvium:sarvagun:session:{session_id}"
        try:
            records = _redis_command("LRANGE", key, "0", str(max(0, limit - 1)))
            if isinstance(records, list):
                return [json.loads(record) for record in records if isinstance(record, str)]
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
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
    metadata = metadata or {}
    record = {
        "id": memory_id,
        "title": metadata.get("title", memory_id),
        "text": text,
        "memory_type": metadata.get("memory_type", "long_term"),
        "trust_scope": metadata.get("trust_scope", "untrusted_external_memory"),
        "metadata": metadata,
        "created_at": _now(),
    }
    upsert_vector_records([record], kind="memory")
    return record


def search_long_term_memory(
    query: str,
    *,
    limit: int = 8,
    trusted_only: bool = False,
) -> List[Dict[str, Any]]:
    search_limit = max(limit * 8, 64) if trusted_only else limit
    records = vector_search(query, limit=search_limit, kind="memory")
    if trusted_only:
        records = [
            record
            for record in records
            if (record.get("trust_scope") or record.get("metadata", {}).get("trust_scope"))
            == "superturiya_evaluated_memory"
            and (record.get("memory_type") or record.get("metadata", {}).get("memory_type"))
            in {"trajectory_summary", "sarvagun_transcript"}
        ]
    return records[:limit]


def index_trajectory_memory(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = run_payload["run_id"]
    final_actions = run_payload.get("final_actions", [])
    evaluation = run_payload.get("evaluation", {})
    sarvagun = run_payload.get("sarvagun") or {}
    superturiya = run_payload.get("superturiya") or {}
    text = json.dumps(
        {
            "run_id": run_id,
            "selected_ticket_ids": run_payload.get("selected_ticket_ids", []),
            "final_actions": final_actions,
            "evaluation_summary": evaluation.get("summary"),
            "metrics": evaluation.get("metrics"),
            "diagnosis": evaluation.get("diagnosis", []),
            "recommendations": evaluation.get("recommendations", []),
            "sarvagun_execution_strategy": sarvagun.get("execution_strategy"),
            "sarvagun_recontact": sarvagun.get("recontact"),
            "sarvagun_incident": sarvagun.get("incident"),
            "sarvagun_satisfaction": sarvagun.get("satisfaction"),
            "superturiya_successes": superturiya.get("successes", []),
            "superturiya_failures": superturiya.get("failures", []),
            "superturiya_intelligence": superturiya.get("intelligence", []),
            "superturiya_feedback_loop_status": superturiya.get("feedback_loop_status"),
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
        metadata={
            "title": f"Long-term summary for {run_id}",
            "memory_type": "trajectory_summary",
            "trust_scope": "superturiya_evaluated_memory",
            "run_id": run_id,
        },
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
        "short_term_namespace": "anirvium:sarvagun:session:*",
        "long_term_role": "vector_database_semantic_memory",
    }
