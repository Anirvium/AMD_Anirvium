import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from app.schemas.ticket import SupportTicket
from app.services.knowledge_base import load_curated_kb_records


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_json(filename: str) -> Any:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache
def load_tickets(dataset: str = "enterprise_saas") -> List[SupportTicket]:
    filename = "customer_support_tickets.json" if dataset == "customer_support" else "synthetic_tickets.json"
    return [SupportTicket(**item) for item in _read_json(filename)]


@lru_cache
def load_customer_support_tickets() -> List[SupportTicket]:
    return load_tickets("customer_support")


@lru_cache
def load_customers() -> List[Dict[str, Any]]:
    return _read_json("synthetic_customers.json")


@lru_cache
def load_kb_articles() -> List[Dict[str, Any]]:
    return _read_json("synthetic_kb.json")


@lru_cache
def load_policies() -> List[Dict[str, Any]]:
    return _read_json("synthetic_policies.json")


def evidence_catalog() -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}
    for item in load_kb_articles() + load_policies():
        catalog[item["id"]] = item
    for item in load_curated_kb_records():
        catalog[item["id"]] = {
            **item,
            "category": f"kb_{item.get('layer', item.get('chunk_type', 'record'))}",
            "summary": item.get("trigger")
            or item.get("customer_safe_summary")
            or item.get("template")
            or item.get("ticket")
            or item.get("title"),
        }
    return catalog


def customers_by_id() -> Dict[str, Dict[str, Any]]:
    return {customer["customer_id"]: customer for customer in load_customers()}
