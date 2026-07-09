import { Gauge, Timer, Wrench } from "lucide-react";
import type { TrajectorySpan } from "../api/types";

interface TraceViewerProps {
  spans: TrajectorySpan[];
}

export default function TraceViewer({ spans }: TraceViewerProps) {
  return (
    <section className="panel trace-viewer">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Trace</p>
          <h2>Reasoning Trace Viewer</h2>
        </div>
      </div>
      <div className="trace-list">
        {spans.length === 0 && <span className="empty-state">Load a run to inspect agent reasoning spans.</span>}
        {spans.map((span) => (
          <article key={span.step_id} className="trace-step">
            <div className="trace-title">
              <div>
                <strong>{span.step_id} · {span.agent_name}</strong>
                <span>{span.input_summary}</span>
              </div>
              <span className="confidence">{Math.round(span.confidence * 100)}%</span>
            </div>
            <p className="trace-output">{span.output_summary}</p>
            {span.reasoning_summary && (
              <p className="trace-reasoning">{span.reasoning_summary}</p>
            )}
            <div className="trace-metrics">
              <span><Timer size={14} />{span.latency_ms} ms</span>
              <span><Gauge size={14} />{span.tokens_in + span.tokens_out} tokens</span>
              <span><Wrench size={14} />{span.tools_used.join(", ") || "none"}</span>
              <span>{span.model_name}</span>
              <span>{span.approval_state.replaceAll("_", " ")}</span>
            </div>
            <div className="evidence-row">
              {span.risk_flags.map((flag) => (
                <span key={flag} className="risk-chip">{flag}</span>
              ))}
              {span.evidence_ids.map((id) => (
                <span key={id}>{id}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
