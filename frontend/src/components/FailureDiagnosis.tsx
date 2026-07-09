import { AlertOctagon } from "lucide-react";
import type { DiagnosisItem } from "../api/types";

interface FailureDiagnosisProps {
  diagnosis: DiagnosisItem[];
}

export default function FailureDiagnosis({ diagnosis }: FailureDiagnosisProps) {
  return (
    <section className="panel diagnosis">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Diagnosis</p>
          <h2>Failure Signals</h2>
        </div>
        <span className="count-pill">{diagnosis.length}</span>
      </div>
      <div className="diagnosis-list">
        {diagnosis.map((item, index) => (
          <article key={`${item.category}-${item.ticket_id ?? index}`} className={`diagnosis-item severity-${item.severity}`}>
            <AlertOctagon size={18} />
            <div>
              <div className="diagnosis-title">
                <strong>{(item.failure_type || item.category).replaceAll("_", " ")} {item.ticket_id ? `· ${item.ticket_id}` : ""}</strong>
                <span>{item.severity}</span>
              </div>
              <p>{item.message}</p>
              {item.affected_agent && <span>Affected agent: {item.affected_agent}</span>}
              {item.business_impact && <span>Impact: {item.business_impact}</span>}
              <span>Fix: {item.recommended_fix || item.suggested_fix}</span>
              {item.metric_impact.length > 0 && <span>Metrics: {item.metric_impact.join(", ")}</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
