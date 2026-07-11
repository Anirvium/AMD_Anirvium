from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List


LAYER_DIR = Path(__file__).resolve().parent.parent / "data" / "kb_layers"
LAYER_FILES = {
    "policies": "policies.json",
    "procedures": "procedures.json",
    "templates": "templates.json",
    "eval_cases": "eval_cases.json",
}

DOMAIN_TERMS = {
    "account_access": {"account", "email", "password", "login", "balance", "registered", "access"},
    "bonuses": {"bonus", "promo", "promocode", "reward", "turnover", "offer"},
    "channel_ops": {"chat", "call", "email", "callback", "close", "closure", "tone"},
    "deposits": {"deposit", "upi", "card", "payment", "paid", "transaction", "screenshot"},
    "priority_support": {"priority", "expert", "hotline", "vip"},
    "verification": {"kyc", "verify", "verification", "document", "selfie", "restricted", "blocked", "unblock"},
    "withdrawals": {"withdrawal", "withdraw", "bank", "utr", "imps", "processed", "limit", "funds"},
}

ISSUE_DOMAIN = {
    "deposit_missing": "deposits",
    "withdrawal_processed_missing": "withdrawals",
    "verification_restriction": "verification",
    "bonus_dispute": "bonuses",
    "cross_account_access": "account_access",
    "priority_policy_exception": "priority_support",
}


def _read_layer(filename: str) -> List[Dict[str, Any]]:
    with (LAYER_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache
def load_kb_layer(layer: str) -> List[Dict[str, Any]]:
    if layer not in LAYER_FILES:
        raise ValueError(f"Unknown KB layer: {layer}")
    return _read_layer(LAYER_FILES[layer])


@lru_cache
def load_kb_layers() -> Dict[str, List[Dict[str, Any]]]:
    return {layer: load_kb_layer(layer) for layer in LAYER_FILES}


@lru_cache
def load_curated_kb_records() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for layer, items in load_kb_layers().items():
        for item in items:
            records.append({**item, "layer": item.get("layer", layer)})
    return records


def kb_layer_summary() -> Dict[str, Any]:
    layers = load_kb_layers()
    return {
        "layer_count": len(layers),
        "record_count": sum(len(items) for items in layers.values()),
        "layers": {
            layer: {
                "count": len(items),
                "domains": sorted({item.get("domain", "unknown") for item in items}),
                "high_risk_count": sum(1 for item in items if item.get("risk_level") == "high"),
            }
            for layer, items in layers.items()
        },
    }


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def record_search_text(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "id",
        "title",
        "domain",
        "trigger",
        "customer_safe_summary",
        "template",
        "ticket",
    ):
        value = record.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("allowed_actions", "prohibited_actions", "steps", "unsafe_outputs", "expected_evidence_ids"):
        values = record.get(key, [])
        if isinstance(values, list):
            parts.extend(str(value) for value in values)
    return " ".join(parts)


def _domain_boost(query_tokens: set[str], domain: str) -> int:
    domain_tokens = DOMAIN_TERMS.get(domain, set())
    return len(query_tokens & domain_tokens)


def search_kb_records(
    query: str,
    *,
    layers: Iterable[str] | None = None,
    limit: int = 8,
    generation_only: bool = False,
) -> List[Dict[str, Any]]:
    query_tokens = _tokens(query)
    allowed_layers = set(layers or LAYER_FILES)
    scored: List[tuple[int, Dict[str, Any]]] = []

    for record in load_curated_kb_records():
        if record.get("layer") not in allowed_layers:
            continue
        if generation_only and not record.get("allowed_for_generation", False):
            continue
        text_tokens = _tokens(record_search_text(record))
        lexical_overlap = len(query_tokens & text_tokens)
        domain_score = _domain_boost(query_tokens, record.get("domain", ""))
        risk_score = 1 if record.get("risk_level") == "high" else 0
        score = lexical_overlap + (2 * domain_score) + risk_score
        if score > 0:
            scored.append((score, record))

    scored.sort(key=lambda item: (item[0], item[1].get("risk_level") == "high"), reverse=True)
    return [record for _, record in scored[:limit]]


def match_records_for_ticket(ticket: Any, *, limit: int = 6) -> List[Dict[str, Any]]:
    query = f"{ticket.issue_type} {ticket.priority} {ticket.message} {' '.join(ticket.previous_interactions)}"
    lexical_records = search_kb_records(
        query,
        layers=("policies", "procedures", "templates"),
        limit=limit,
    )
    try:
        from app.services.vector_store import hybrid_kb_search

        matches = hybrid_kb_search(
            query,
            lexical_records,
            limit=limit,
            allowed_layers=("policies", "procedures", "templates"),
        )
        domain = ISSUE_DOMAIN.get(ticket.issue_type)
        if domain:
            matches = [record for record in matches if record.get("domain") == domain]
        return matches[:limit]
    except Exception:
        return lexical_records


def records_as_evidence(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence_cards = []
    for record in records:
        summary = (
            record.get("trigger")
            or record.get("customer_safe_summary")
            or record.get("template")
            or record.get("ticket")
            or record.get("title")
        )
        evidence_cards.append(
            {
                "id": record["id"],
                "title": record["title"],
                "summary": summary,
                "category": f"kb_{record.get('layer', record.get('chunk_type', 'record'))}",
                "domain": record.get("domain"),
                "risk_level": record.get("risk_level"),
                "requires_approval": record.get("requires_approval", False),
                "allowed_for_generation": record.get("allowed_for_generation", False),
            }
        )
    return evidence_cards
