import { AlertTriangle, LockKeyhole, ShieldCheck } from "lucide-react";
import type { RunResult } from "../api/types";

interface PolicyGuardrailPanelProps {
  run: RunResult | null;
}

export default function PolicyGuardrailPanel({ run }: PolicyGuardrailPanelProps) {
  const actions = run?.final_actions ?? [];
  const approvalRequired = actions.filter((action) => action.approval_state === "APPROVAL_REQUIRED");
  const escalated = actions.filter((action) => action.approval_state === "ESCALATED");
  const riskFlags = Array.from(new Set(actions.flatMap((action) => action.risk_flags)));
  const policySpans = run?.trajectory.filter((span) => span.agent_name.toLowerCase().includes("policy") || span.approval_state !== "DRAFT_RECOMMENDATION") ?? [];

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
          <span>Escalated safely</span>
          <strong>{escalated.length}</strong>
        </div>
      </div>

      <div className="policy-list">
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
