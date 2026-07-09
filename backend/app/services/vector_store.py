from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Iterable, List

import httpx

from app.config import get_settings
from app.services.knowledge_base import load_curated_kb_records, record_search_text


_LOCAL_INDEXES: Dict[str, List[Dict[str, Any]]] = {}


def embed_text(text: str, dimension: int | None = None) -> List[float]:
    """Deterministic embedding used for local retrieval and pre-GPU tests.

    GPU deployment can replace this with the configured embedding model while
    preserving the same vector-store interface.
    """

    settings = get_settings()
    size = dimension or settings.vector_dimension
    vector = [0.0] * size
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % size
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _cosine(left: List[float], right: List[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _point_id(record_id: str) -> int:
    digest = hashlib.sha256(record_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _payload(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": record["id"],
        "title": record["title"],
        "layer": record.get("layer"),
        "domain": record.get("domain"),
        "risk_level": record.get("risk_level"),
        "requires_approval": record.get("requires_approval", False),
        "allowed_for_generation": record.get("allowed_for_generation", False),
    }


def _collection_name(kind: str) -> str:
    settings = get_settings()
    if kind == "memory":
        return settings.vector_memory_collection
    if kind == "trajectory":
        return settings.vector_trajectory_collection
    return settings.vector_kb_collection


def _ensure_qdrant_collection(collection: str) -> None:
    settings = get_settings()
    with httpx.Client(timeout=20) as client:
        client.put(
            f"{settings.vector_base_url.rstrip('/')}/collections/{collection}",
            json={"vectors": {"size": settings.vector_dimension, "distance": "Cosine"}},
        ).raise_for_status()


def upsert_vector_records(records: List[Dict[str, Any]], *, kind: str = "kb") -> Dict[str, Any]:
    settings = get_settings()
    collection = _collection_name(kind)
    points = [
        {
            "id": _point_id(record["id"]),
            "vector": embed_text(record.get("text", record.get("title", record["id"])), settings.vector_dimension),
            "payload": record,
            "record": record,
        }
        for record in records
    ]

    if settings.vector_backend == "qdrant":
        _ensure_qdrant_collection(collection)
        with httpx.Client(timeout=20) as client:
            client.put(
                f"{settings.vector_base_url.rstrip('/')}/collections/{collection}/points",
                params={"wait": "true"},
                json={"points": [{"id": p["id"], "vector": p["vector"], "payload": p["payload"]} for p in points]},
            ).raise_for_status()
    else:
        index = _LOCAL_INDEXES.setdefault(collection, [])
        existing_ids = {item["record"]["id"] for item in index}
        index[:] = [item for item in index if item["record"]["id"] not in {record["id"] for record in records}]
        index.extend(points)
        existing_ids.update(record["id"] for record in records)

    return {
        "backend": settings.vector_backend,
        "collection": collection,
        "dimension": settings.vector_dimension,
        "indexed_records": len(points),
    }


def reindex_kb_vectors() -> Dict[str, Any]:
    settings = get_settings()
    collection = _collection_name("kb")
    records = load_curated_kb_records()
    vector_records = [
        {
            **_payload(record),
            "id": record["id"],
            "text": record_search_text(record),
        }
        for record in records
    ]
    _LOCAL_INDEXES[collection] = []
    result = upsert_vector_records(vector_records, kind="kb")
    result["indexed_records"] = len(records)
    return result


def vector_status() -> Dict[str, Any]:
    settings = get_settings()
    collections = {
        "kb": settings.vector_kb_collection,
        "memory": settings.vector_memory_collection,
        "trajectory": settings.vector_trajectory_collection,
    }
    status = {
        "backend": settings.vector_backend,
        "collections": collections,
        "dimension": settings.vector_dimension,
        "local_index_sizes": {name: len(_LOCAL_INDEXES.get(collection, [])) for name, collection in collections.items()},
        "qdrant_reachable": False,
    }
    if settings.vector_backend == "qdrant":
        qdrant_collections: Dict[str, Any] = {}
        try:
            for name, collection in collections.items():
                response = httpx.get(f"{settings.vector_base_url.rstrip('/')}/collections/{collection}", timeout=5)
                qdrant_collections[name] = {"reachable": response.status_code == 200}
                if response.status_code == 200:
                    result = response.json().get("result", {})
                    qdrant_collections[name]["points_count"] = result.get("points_count")
            status["qdrant_reachable"] = any(item.get("reachable") for item in qdrant_collections.values())
            status["qdrant_collections"] = qdrant_collections
        except httpx.HTTPError:
            status["qdrant_reachable"] = False
    return status


def _records_by_id() -> Dict[str, Dict[str, Any]]:
    return {record["id"]: record for record in load_curated_kb_records()}


def vector_search(query: str, *, limit: int = 8, kind: str = "kb") -> List[Dict[str, Any]]:
    settings = get_settings()
    collection = _collection_name(kind)
    vector = embed_text(query, settings.vector_dimension)

    if settings.vector_backend == "qdrant":
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    f"{settings.vector_base_url.rstrip('/')}/collections/{collection}/points/search",
                    json={"vector": vector, "limit": limit, "with_payload": True},
                )
                response.raise_for_status()
            by_id = _records_by_id() if kind == "kb" else {}
            records: List[Dict[str, Any]] = []
            for point in response.json().get("result", []):
                record_id = point.get("payload", {}).get("id")
                if record_id in by_id:
                    records.append({**by_id[record_id], "vector_score": point.get("score", 0.0)})
                elif point.get("payload"):
                    records.append({**point["payload"], "vector_score": point.get("score", 0.0)})
            return records
        except httpx.HTTPError:
            return []

    if kind == "kb" and not _LOCAL_INDEXES.get(collection):
        reindex_kb_vectors()
    index = _LOCAL_INDEXES.get(collection, [])
    scored = [
        (_cosine(vector, item["vector"]), item["record"])
        for item in index
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{**record, "vector_score": round(score, 4)} for score, record in scored[:limit]]


def hybrid_kb_search(query: str, lexical_records: Iterable[Dict[str, Any]], *, limit: int = 8) -> List[Dict[str, Any]]:
    combined: Dict[str, Dict[str, Any]] = {}
    for rank, record in enumerate(lexical_records, start=1):
        combined[record["id"]] = {**record, "hybrid_score": 1.0 / rank, "retrieval_source": "lexical"}
    for rank, record in enumerate(vector_search(query, limit=limit), start=1):
        current = combined.get(record["id"], record)
        current["hybrid_score"] = current.get("hybrid_score", 0.0) + 1.0 / rank
        current["vector_score"] = record.get("vector_score")
        current["retrieval_source"] = "hybrid" if record["id"] in combined else "vector"
        combined[record["id"]] = current
    results = list(combined.values())
    results.sort(key=lambda item: item.get("hybrid_score", 0.0), reverse=True)
    return results[:limit]
