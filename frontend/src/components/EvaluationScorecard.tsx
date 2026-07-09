import type { EvaluationMetrics } from "../api/types";

interface EvaluationScorecardProps {
  metrics?: EvaluationMetrics;
}

const labels: Array<[keyof EvaluationMetrics, string, boolean]> = [
  ["task_completion", "Task Completion", false],
  ["evidence_grounding", "Evidence Grounding", false],
  ["policy_compliance", "Policy Compliance", false],
  ["hallucination_risk", "Hallucination Risk", true],
  ["escalation_quality", "Escalation Quality", false],
  ["actionability", "Actionability", false],
  ["missing_information", "Missing Information", true],
  ["customer_tone", "Customer Tone", false],
  ["token_efficiency", "Token Efficiency", false],
  ["latency_efficiency", "Latency Efficiency", false]
];

export default function EvaluationScorecard({ metrics }: EvaluationScorecardProps) {
  return (
    <section className="panel scorecard">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Evaluation</p>
          <h2>Trajectory Health</h2>
        </div>
        <span className="score-badge">{metrics ? `${metrics.overall_score}` : "--"}</span>
      </div>
      <div className="metric-grid">
        {labels.map(([key, label, inverse]) => {
          const value = metrics?.[key] ?? 0;
          const display = Math.round(value * 100);
          return (
            <div key={key} className="metric-row">
              <div>
                <span>{label}</span>
                <strong>{display}%</strong>
              </div>
              <div className={`bar ${inverse ? "inverse" : ""}`}>
                <span style={{ width: `${display}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

