from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.trajectory import ApprovalState
from app.schemas.visual_evidence import VisualEvidenceCard, VisualEvidenceSourceType


class VisualEvidenceAgent:
    name = "Attachment Evidence Agent"

    def __init__(self, *_: Any, **__: Any) -> None:
        self.model_name = "deterministic-attachment-evidence"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        cards: List[VisualEvidenceCard] = []
        risk_flags: List[str] = []

        for ticket in context["tickets"]:
            for index, attachment in enumerate(ticket.attachments, start=1):
                card = self._build_card(ticket, attachment, index, self.model_name)
                cards.append(card)
                risk_flags.extend(card.risk_flags)

        by_ticket: Dict[str, List[Dict[str, Any]]] = {}
        for card in cards:
            by_ticket.setdefault(card.ticket_id, []).append(card.model_dump())

        context["visual_evidence_cards"] = [card.model_dump() for card in cards]
        context["visual_evidence_by_ticket"] = by_ticket

        return {
            "summary": f"Extracted {len(cards)} attachment evidence cards without loading an image/video model.",
            "visual_evidence_cards": [card.model_dump() for card in cards],
            "tools_used": ["attachment_metadata_parser", "evidence_card_generator"],
            "evidence_ids": [card.evidence_id for card in cards],
            "risk_flags": sorted(set(risk_flags)),
            "approval_state": ApprovalState.DRAFT_RECOMMENDATION.value,
            "model_name": self.model_name,
            "confidence": 0.86 if cards else 0.8,
        }

    def _build_card(self, ticket: Any, attachment: Dict[str, Any], index: int, model_name: str) -> VisualEvidenceCard:
        filename = str(attachment.get("filename", f"attachment-{index}"))
        mime_type = str(attachment.get("type", "unknown"))
        source_type = self._source_type(filename, mime_type)
        evidence_id = f"VIS-{ticket.ticket_id.split('-')[-1]}-{index:02d}"
        findings = self._findings_for_ticket(ticket.issue_type, filename, source_type)
        risk_flags = self._risk_flags_for_ticket(ticket.issue_type, source_type)
        supported_claims = self._supported_claims_for_ticket(ticket.issue_type, ticket.message)
        requires_policy_check = bool(risk_flags) or ticket.issue_type in {
            "billing_refund",
            "security_data_deletion",
            "production_outage",
            "integration_failure",
        }

        return VisualEvidenceCard(
            evidence_id=evidence_id,
            ticket_id=ticket.ticket_id,
            source_type=source_type,
            filename=filename,
            summary=self._summary(ticket.issue_type, filename, source_type),
            ocr_text=self._mock_ocr(ticket.issue_type, filename, source_type),
            visual_findings=findings,
            timestamp_refs=self._timestamp_refs(ticket.issue_type, source_type),
            supported_claims=supported_claims,
            risk_flags=risk_flags,
            confidence=0.88 if source_type in {"image", "screenshot", "structured_log"} else 0.8,
            requires_policy_check=requires_policy_check,
            model_name=model_name,
            raw_modality=mime_type,
        )

    def _source_type(self, filename: str, mime_type: str) -> VisualEvidenceSourceType:
        lowered = f"{filename} {mime_type}".lower()
        if any(token in lowered for token in ["screenshot", ".png", ".jpg", ".jpeg", "image/"]):
            return "screenshot" if "screenshot" in lowered else "image"
        if any(token in lowered for token in [".mp4", ".mov", ".webm", "video/"]):
            return "video"
        if any(token in lowered for token in [".pdf", "application/pdf"]):
            return "document"
        if any(token in lowered for token in [".json", "application/json"]):
            return "structured_log"
        if any(token in lowered for token in [".txt", "text/plain"]):
            return "text_attachment"
        return "unknown"

    def _summary(self, issue_type: str, filename: str, source_type: VisualEvidenceSourceType) -> str:
        if issue_type == "production_outage":
            return f"{filename} appears to support the outage report with customer-provided availability context."
        if issue_type == "billing_refund":
            return f"{filename} is treated as billing evidence that needs invoice verification before any refund commitment."
        if issue_type == "security_data_deletion":
            return f"{filename} is security-sensitive supporting material that requires authority verification."
        if issue_type == "integration_failure":
            return f"{filename} provides integration failure evidence for connector/authentication triage."
        return f"{filename} captured as {source_type.replace('_', ' ')} support evidence."

    def _mock_ocr(self, issue_type: str, filename: str, source_type: VisualEvidenceSourceType) -> str:
        if issue_type == "production_outage":
            return "Status: degraded availability; region: EU; impact: production workspace unavailable."
        if issue_type == "billing_refund":
            return "Invoice evidence redacted; duplicate annual plan charge requires billing review."
        if issue_type == "security_data_deletion":
            return "Audit request redacted; deletion and access confirmation requested."
        if issue_type == "integration_failure":
            return "Sync error payload redacted; authentication or connector retry failure indicated."
        if source_type in {"image", "screenshot", "video"}:
            return "Customer-provided visual context captured for support review."
        return ""

    def _findings_for_ticket(self, issue_type: str, filename: str, source_type: VisualEvidenceSourceType) -> List[str]:
        if issue_type == "production_outage":
            return ["availability impact is visible", "EU region context is present", "status evidence supports SLA escalation"]
        if issue_type == "billing_refund":
            return ["invoice artifact is present", "refund claim requires billing approval", "written confirmation should be gated"]
        if issue_type == "security_data_deletion":
            return ["audit-related attachment is present", "identity and authority verification required", "deletion confirmation must be gated"]
        if issue_type == "integration_failure":
            return ["sync error artifact is present", "connector authentication context should be inspected", "deadline impact supports escalation"]
        if source_type in {"image", "screenshot"}:
            return ["visual customer evidence is available"]
        if source_type == "video":
            return ["video evidence is available for temporal review"]
        return [f"{filename} is available for support review"]

    def _risk_flags_for_ticket(self, issue_type: str, source_type: VisualEvidenceSourceType) -> List[str]:
        flags: List[str] = []
        if source_type in {"image", "screenshot", "video"}:
            flags.append("MULTIMODAL_EVIDENCE_PRESENT")
        if issue_type == "billing_refund":
            flags.append("VISUAL_BILLING_EVIDENCE_REQUIRES_APPROVAL")
        if issue_type == "security_data_deletion":
            flags.append("VISUAL_SECURITY_EVIDENCE_REQUIRES_APPROVAL")
        if issue_type in {"production_outage", "integration_failure"}:
            flags.append("VISUAL_SLA_EVIDENCE")
        return flags

    def _supported_claims_for_ticket(self, issue_type: str, message: str) -> List[str]:
        if issue_type == "production_outage":
            return ["production availability is impacted", "SLA escalation is justified"]
        if issue_type == "billing_refund":
            return ["billing dispute has supporting material", "refund confirmation still requires approval"]
        if issue_type == "security_data_deletion":
            return ["security-sensitive request has supporting material", "final confirmation requires security review"]
        if issue_type == "integration_failure":
            return ["integration failure has technical supporting material", "engineering escalation is justified"]
        return [message[:120]]

    def _timestamp_refs(self, issue_type: str, source_type: VisualEvidenceSourceType) -> List[str]:
        if source_type == "video":
            return ["00:00-00:15"]
        if issue_type in {"production_outage", "integration_failure"}:
            return ["customer-reported incident window"]
        return []
