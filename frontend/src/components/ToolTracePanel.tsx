import { Braces, Wrench } from "lucide-react";
import type { TrajectorySpan } from "../api/types";

interface ToolTracePanelProps {
  spans: TrajectorySpan[];
}

export default function ToolTracePanel({ spans }: ToolTracePanelProps) {
  const rows = spans.flatMap((span) => {
    const tools = span.tools_used.length > 0 ? span.tools_used : ["deterministic_agent_step"];
    return tools.map((tool) => ({ span, tool }));
  });

  return (
    <section className="panel tool-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Tool Calls</p>
          <h2>Action Trace</h2>
        </div>
        <span className="count-pill">{rows.length || "--"}</span>
      </div>

      <div className="tool-list">
        {rows.length === 0 && <span className="empty-state">No run loaded yet.</span>}
        {rows.map(({ span, tool }, index) => (
          <article key={`${span.step_id}-${tool}-${index}`} className="tool-item">
            <div>
              <Wrench size={16} />
              <strong>{tool.replaceAll("_", " ")}</strong>
            </div>
            <p>{span.agent_name} produced: {span.output_summary}</p>
            <div className="tool-meta">
              <span><Braces size={13} />{Object.keys(span.full_output ?? {}).length} output fields</span>
              <span>{span.tokens_in + span.tokens_out} tokens</span>
              <span>{span.evidence_ids.join(", ") || "no evidence"}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
