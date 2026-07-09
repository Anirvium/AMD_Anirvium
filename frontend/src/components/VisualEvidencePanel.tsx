import { Camera, Clock, FileSearch, ShieldAlert } from "lucide-react";
import type { VisualEvidenceCard } from "../api/types";

interface VisualEvidencePanelProps {
  cards: VisualEvidenceCard[];
}

export default function VisualEvidencePanel({ cards }: VisualEvidencePanelProps) {
  return (
    <section className="panel visual-evidence-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Attachments</p>
          <h2>Evidence + Citations</h2>
        </div>
        <span className="count-pill">{cards.length}</span>
      </div>

      <div className="visual-evidence-list">
        {cards.map((card) => (
          <article key={card.evidence_id} className="visual-evidence-card">
            <div className="visual-evidence-title">
              <div>
                <strong><Camera size={15} />{card.evidence_id} · {card.filename}</strong>
                <span>{card.ticket_id} · {card.source_type.replaceAll("_", " ")}</span>
              </div>
              {card.requires_policy_check && (
                <span className="visual-policy">
                  <ShieldAlert size={14} />
                  policy check
                </span>
              )}
            </div>
            <p>{card.summary}</p>
            {card.ocr_text && (
              <div className="ocr-box">
                <FileSearch size={14} />
                <span>{card.ocr_text}</span>
              </div>
            )}
            <div className="visual-findings">
              {card.visual_findings.map((finding) => (
                <span key={finding}>{finding}</span>
              ))}
            </div>
            {card.timestamp_refs.length > 0 && (
              <div className="timestamp-row">
                <Clock size={14} />
                {card.timestamp_refs.join(", ")}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
