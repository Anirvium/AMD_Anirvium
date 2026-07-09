import { CheckCircle2, FileText, ShieldAlert, UserRoundCheck } from "lucide-react";
import type { FinalAction } from "../api/types";

interface FinalActionsProps {
  actions: FinalAction[];
}

export default function FinalActions({ actions }: FinalActionsProps) {
  const statusLabel = (value?: string | null) => value ? value.replaceAll("_", " ") : "not checked";

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
            <div className="action-meta-strip">
              <span className={`compliance-pill compliance-${(action.compliance_status ?? "not_checked").toLowerCase()}`}>
                <ShieldAlert size={13} />
                {statusLabel(action.compliance_status)}
              </span>
              <span className="confidence-pill">
                <CheckCircle2 size={13} />
                {Math.round((action.confidence_score ?? 0.86) * 100)}% confidence
              </span>
              {action.human_escalation_required && (
                <span className="handoff-pill">
                  <UserRoundCheck size={13} />
                  human review
                </span>
              )}
            </div>
            <p>{action.draft_response}</p>
            {action.handoff_summary && <p className="handoff-summary">{action.handoff_summary}</p>}
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
