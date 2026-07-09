from __future__ import annotations

from app.agents.retrieval_agent import KnowledgeRetrievalAgent
from app.schemas.ticket import SupportTicket
from app.services.knowledge_base import (
    kb_layer_summary,
    load_kb_layer,
    match_records_for_ticket,
    search_kb_records,
)
from app.services.vector_store import reindex_kb_vectors, vector_search, vector_status


def test_kb_layers_have_required_seed_records() -> None:
    summary = kb_layer_summary()

    assert summary["layer_count"] == 4
    assert summary["record_count"] >= 30
    assert summary["layers"]["policies"]["high_risk_count"] >= 4

    for layer in ("policies", "procedures", "templates", "eval_cases"):
        records = load_kb_layer(layer)
        assert records
        assert all(record["id"] for record in records)
        assert all(record["domain"] for record in records)


def test_kb_search_finds_withdrawal_policy_and_template() -> None:
    records = search_kb_records("processed withdrawal not received bank statement", limit=6)
    ids = {record["id"] for record in records}

    assert "POL-CS-PAY-002" in ids
    assert "PROC-CS-WDR-001" in ids
    assert "TMPL-CS-WDR-002" in ids


def test_ticket_matching_returns_curated_evidence() -> None:
    ticket = SupportTicket(
        ticket_id="T-KB-001",
        customer_id="C-KB-001",
        customer_name="Demo Customer",
        plan="business",
        issue_type="withdrawal",
        priority="high",
        message="My withdrawal is processed but the bank did not receive it after 5 working days.",
        created_at="2026-07-09T00:00:00Z",
        sla_deadline="2026-07-09T04:00:00Z",
        sentiment="frustrated",
        expected_evidence_ids=[],
    )

    matches = match_records_for_ticket(ticket, limit=5)
    ids = {record["id"] for record in matches}

    assert "POL-CS-PAY-002" in ids
    assert "PROC-CS-WDR-001" in ids


def test_retrieval_agent_adds_curated_kb_cards() -> None:
    ticket = SupportTicket(
        ticket_id="T-KB-002",
        customer_id="C-KB-002",
        customer_name="Demo Customer",
        plan="business",
        issue_type="verification",
        priority="high",
        message="My account is restricted for KYC and I need it unblocked immediately.",
        created_at="2026-07-09T00:00:00Z",
        sla_deadline="2026-07-09T04:00:00Z",
        sentiment="angry",
        expected_evidence_ids=[],
    )
    context = {
        "tickets": [ticket],
        "evidence_catalog": {},
        "visual_evidence_by_ticket": {},
    }

    result = KnowledgeRetrievalAgent().run(context)
    retrieved_ids = {card["id"] for card in context["retrieved_evidence"][ticket.ticket_id]}

    assert "POL-CS-VERIFY-001" in retrieved_ids
    assert "PROC-CS-VERIFY-001" in retrieved_ids
    assert "POL-CS-VERIFY-001" in result["evidence_ids"]


def test_local_vector_index_retrieves_curated_records() -> None:
    result = reindex_kb_vectors()
    status = vector_status()
    matches = vector_search("withdrawal processed bank statement", limit=5)
    ids = {record["id"] for record in matches}

    assert result["indexed_records"] >= 30
    assert status["backend"] == "local"
    assert status["local_index_sizes"]["kb"] >= 30
    assert "POL-CS-PAY-002" in ids or "PROC-CS-WDR-001" in ids
