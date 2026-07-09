import { CheckCircle2, Clock3, GitCommitHorizontal, ShieldAlert } from "lucide-react";
import type { TrajectorySpan } from "../api/types";

interface TrajectoryTimelineProps {
  spans: TrajectorySpan[];
}

export default function TrajectoryTimeline({ spans }: TrajectoryTimelineProps) {
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Trajectory Timeline</p>
          <h2>Agent Reasoning Path</h2>
        </div>
        <span className="count-pill">{spans.length || "--"}</span>
      </div>

      <div className="timeline-list">
        {spans.length === 0 && (
          <article className="timeline-empty">
            <GitCommitHorizontal size={18} />
            <span>Load the support KB demo to reveal the full agent trajectory.</span>
          </article>
        )}
        {spans.map((span, index) => {
          const approvalRequired = span.approval_state === "APPROVAL_REQUIRED";
          return (
            <article key={span.step_id} className="timeline-item">
              <div className="timeline-index">{String(index + 1).padStart(2, "0")}</div>
              <div className="timeline-body">
                <div className="timeline-title">
                  <strong>{span.agent_name}</strong>
                  <span className={`timeline-state ${approvalRequired ? "warn" : "ok"}`}>
                    {approvalRequired ? <ShieldAlert size={14} /> : <CheckCircle2 size={14} />}
                    {span.approval_state.replaceAll("_", " ")}
                  </span>
                </div>
                <p>{span.output_summary}</p>
                <div className="timeline-meta">
                  <span><Clock3 size={13} />{span.latency_ms} ms</span>
                  <span>{span.tools_used.length} tools</span>
                  <span>{span.evidence_ids.length} evidence refs</span>
                  <span>{Math.round(span.confidence * 100)} confidence</span>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
