import { CheckCircle2, FileText, ShieldAlert } from "lucide-react";
import type { FinalAction } from "../api/types";

interface FinalActionsProps {
  actions: FinalAction[];
}

export default function FinalActions({ actions }: FinalActionsProps) {
  return (
    <section className="panel final-actions">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Actions</p>
          <h2>Safe Draft Preview</h2>
        </div>
        <span className="count-pill">{actions.length}</span>
      </div>

      <div className="action-list">
        {actions.map((action) => (
          <article key={action.ticket_id} className="action-item">
            <div className="action-header">
              <div>
                <strong>{action.ticket_id} · {action.customer_name}</strong>
                <span>{action.recommended_escalation}</span>
              </div>
              <span className={`approval approval-${action.approval_state.toLowerCase()}`}>
                {action.approval_state === "APPROVAL_REQUIRED" ? <ShieldAlert size={14} /> : <CheckCircle2 size={14} />}
                {action.approval_state.replaceAll("_", " ")}
              </span>
            </div>
            <p>{action.draft_response}</p>
            <div className="evidence-row">
              <FileText size={14} />
              {action.evidence_ids.map((id) => (
                <span key={id}>{id}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
