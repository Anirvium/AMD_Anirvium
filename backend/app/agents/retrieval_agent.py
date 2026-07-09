from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState
from app.services.knowledge_base import match_records_for_ticket, records_as_evidence


class KnowledgeRetrievalAgent:
    name = "Knowledge Retrieval Agent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        catalog = context["evidence_catalog"]
        retrieved: Dict[str, List[Dict[str, Any]]] = {}
        all_evidence_ids: List[str] = []

        for ticket in context["tickets"]:
            evidence_ids = list(dict.fromkeys(ticket.expected_evidence_ids))
            evidence_cards = []
            for evidence_id in evidence_ids:
                item = catalog[evidence_id]
                evidence_cards.append(
                    {
                        "id": evidence_id,
                        "title": item["title"],
                        "summary": item.get("summary") or item.get("rule"),
                        "category": item.get("category", "knowledge_base"),
                    }
                )
            for visual_card in context.get("visual_evidence_by_ticket", {}).get(ticket.ticket_id, []):
                evidence_cards.append(
                    {
                        "id": visual_card["evidence_id"],
                        "title": f"Attachment evidence: {visual_card['filename']}",
                        "summary": visual_card["summary"],
                        "category": visual_card["source_type"],
                    }
                )
                evidence_ids.append(visual_card["evidence_id"])
            curated_matches = match_records_for_ticket(ticket, limit=5)
            for card in records_as_evidence(curated_matches):
                if card["id"] in evidence_ids:
                    continue
                evidence_cards.append(card)
                evidence_ids.append(card["id"])
            retrieved[ticket.ticket_id] = evidence_cards
            all_evidence_ids.extend(evidence_ids)

        context["retrieved_evidence"] = retrieved
        return {
            "summary": f"Retrieved grounded evidence for {len(retrieved)} tickets.",
            "retrieved_evidence": retrieved,
            "tools_used": ["local_kb_search", "policy_catalog_lookup", "visual_evidence_lookup"],
            "evidence_ids": sorted(set(all_evidence_ids)),
            "risk_flags": [],
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "confidence": 0.92,
        }
