import { AlertTriangle, LockKeyhole, ShieldCheck } from "lucide-react";
import type { RunResult } from "../api/types";

interface PolicyGuardrailPanelProps {
  run: RunResult | null;
}

export default function PolicyGuardrailPanel({ run }: PolicyGuardrailPanelProps) {
  const actions = run?.final_actions ?? [];
  const approvalRequired = actions.filter((action) => action.approval_state === "APPROVAL_REQUIRED");
  const humanHandoffs = actions.filter((action) => action.human_escalation_required);
  const complianceReview = actions.filter((action) => ["BLOCKED", "REVIEW_REQUIRED"].includes(action.compliance_status ?? ""));
  const riskFlags = Array.from(new Set(actions.flatMap((action) => action.risk_flags)));
  const policySpans = run?.trajectory.filter((span) => {
    const name = span.agent_name.toLowerCase();
    return name.includes("policy") || name.includes("compliance") || name.includes("human") || span.approval_state !== "DRAFT_RECOMMENDATION";
  }) ?? [];

  return (
    <section className="panel policy-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Policy Assurance</p>
          <h2>Guardrails + Approval States</h2>
        </div>
        <span className="guardrail-chip"><ShieldCheck size={15} />active</span>
      </div>

      <div className="guardrail-grid">
        <div>
          <LockKeyhole size={17} />
          <span>Approval required</span>
          <strong>{approvalRequired.length}</strong>
        </div>
        <div>
          <AlertTriangle size={17} />
          <span>Risk flags</span>
          <strong>{riskFlags.length}</strong>
        </div>
        <div>
          <ShieldCheck size={17} />
          <span>Compliance review</span>
          <strong>{complianceReview.length}</strong>
        </div>
        <div>
          <LockKeyhole size={17} />
          <span>Human handoffs</span>
          <strong>{humanHandoffs.length}</strong>
        </div>
      </div>

      <div className="policy-list">
        {actions.length > 0 && (
          <article>
            <div>
              <strong>Compliance + human escalation agent</strong>
              <span className="approval approval-draft_recommendation">{humanHandoffs.length} human handoff(s)</span>
            </div>
            <p>
              {complianceReview.length
                ? `${complianceReview.length} drafted action(s) require compliance or approval review before send.`
                : "All current drafts passed material compliance checks after safe rewrite filters."}
            </p>
            <div className="evidence-row">
              {actions.map((action) => (
                <span key={action.ticket_id}>
                  {action.ticket_id}: {(action.compliance_status ?? "NOT_CHECKED").replaceAll("_", " ")}
                </span>
              ))}
            </div>
          </article>
        )}
        {(policySpans.length ? policySpans : run?.trajectory.slice(0, 3) ?? []).map((span) => (
          <article key={span.step_id}>
            <div>
              <strong>{span.agent_name}</strong>
              <span className={`approval approval-${span.approval_state.toLowerCase()}`}>{span.approval_state.replaceAll("_", " ")}</span>
            </div>
            <p>{span.output_summary}</p>
            <div className="evidence-row">
              {span.risk_flags.map((flag) => <span key={flag}>{flag}</span>)}
              {span.evidence_ids.map((id) => <span key={id}>{id}</span>)}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
