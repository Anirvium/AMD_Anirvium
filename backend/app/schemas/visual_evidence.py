from typing import List, Literal, Optional

from pydantic import BaseModel, Field


VisualEvidenceSourceType = Literal["image", "video", "screenshot", "document", "text_attachment", "structured_log", "unknown"]


class VisualEvidenceCard(BaseModel):
    evidence_id: str
    ticket_id: str
    source_type: VisualEvidenceSourceType
    filename: str
    summary: str
    ocr_text: str = ""
    visual_findings: List[str] = Field(default_factory=list)
    timestamp_refs: List[str] = Field(default_factory=list)
    supported_claims: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    requires_policy_check: bool = False
    model_name: str = "mock-visual-evidence-model"
    raw_modality: Optional[str] = None
