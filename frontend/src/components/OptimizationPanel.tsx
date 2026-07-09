import { GitBranchPlus } from "lucide-react";
import type { OptimizationRecommendation } from "../api/types";

interface OptimizationPanelProps {
  recommendations: OptimizationRecommendation[];
}

export default function OptimizationPanel({ recommendations }: OptimizationPanelProps) {
  return (
    <section className="panel optimizer">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Optimizer</p>
          <h2>Workflow Fixes</h2>
        </div>
        <span className="count-pill">{recommendations.length}</span>
      </div>
      <div className="optimization-list">
        {recommendations.map((item) => (
          <article key={item.recommendation_id} className="optimization-item">
            <GitBranchPlus size={18} />
            <div>
              <div className="optimization-title">
                <strong>{item.title}</strong>
                <span>{item.priority}</span>
              </div>
              <p>{item.problem || item.rationale}</p>
              {item.target_agent && <small>Target: {item.target_agent}</small>}
              <div className="before-after">
                <span>Root cause: {item.root_cause || item.before}</span>
                <span>Fix: {item.fix || item.after}</span>
              </div>
              {Object.keys(item.expected_metric_lift).length > 0 && (
                <div className="metric-lift">
                  {Object.entries(item.expected_metric_lift).map(([metric, lift]) => (
                    <span key={metric}>{metric}: {lift}</span>
                  ))}
                </div>
              )}
              {item.implementation_hint && <small>{item.implementation_hint}</small>}
              <small>{item.expected_impact}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
