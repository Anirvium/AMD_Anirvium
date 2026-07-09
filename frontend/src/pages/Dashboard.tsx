import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, Clock3, GitBranch, MessageSquareText, ShieldCheck, TrendingUp } from "lucide-react";
import { fetchCustomerSupportDemo, fetchCustomerSupportTickets, runSupportAgent } from "../api/client";
import type { RunResult, SupportTicket } from "../api/types";
import CustomerAgentWorkspace from "../components/CustomerAgentWorkspace";
import EvaluationScorecard from "../components/EvaluationScorecard";
import FailureDiagnosis from "../components/FailureDiagnosis";
import FinalActions from "../components/FinalActions";
import OptimizationPanel from "../components/OptimizationPanel";
import PolicyGuardrailPanel from "../components/PolicyGuardrailPanel";
import TicketQueue from "../components/TicketQueue";
import ToolTracePanel from "../components/ToolTracePanel";
import TraceViewer from "../components/TraceViewer";
import TrajectoryTimeline from "../components/TrajectoryTimeline";
import VisualEvidencePanel from "../components/VisualEvidencePanel";

export default function Dashboard() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [run, setRun] = useState<RunResult | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchCustomerSupportTickets().then(setTickets).catch((err) => setError(err.message));
  }, []);

  const selectedTicketIds = useMemo(
    () => run?.selected_ticket_ids ?? tickets.filter((ticket) => ["high", "critical"].includes(ticket.priority)).map((ticket) => ticket.ticket_id),
    [run, tickets]
  );

  async function handleCustomerQuery(ticketIds: string[], query: string) {
    setIsRunning(true);
    setError(null);
    setLastQuery(query);
    try {
      const result = await runSupportAgent(ticketIds, query);
      setRun(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Support agent failed");
    } finally {
      setIsRunning(false);
    }
  }

  async function handleLoadCustomerSupportDemo() {
    setIsRunning(true);
    setError(null);
    try {
      const [demo, supportTickets] = await Promise.all([fetchCustomerSupportDemo(), fetchCustomerSupportTickets()]);
      setTickets(supportTickets);
      setRun(demo.run);
      setLastQuery(demo.selected_tickets[0]?.message ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Customer support demo failed");
    } finally {
      setIsRunning(false);
    }
  }

  const criticalIssues = run?.evaluation.diagnosis.filter((item) => ["HIGH", "CRITICAL"].includes(item.severity)).length ?? 0;
  const policyGates = run?.final_actions.filter((action) => action.approval_state === "APPROVAL_REQUIRED").length ?? 0;
  const evidenceUsed = run ? new Set(run.final_actions.flatMap((action) => action.evidence_ids)).size : 0;
  const totalLatency = run?.trajectory.reduce((total, span) => total + span.latency_ms, 0) ?? 0;
  const escalationRate = run?.final_actions.length ? Math.round((policyGates / run.final_actions.length) * 100) : 0;
  const customerTone = run ? Math.round(run.evaluation.metrics.customer_tone * 100) : 0;

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Anirvium AI</p>
          <h1>Customer Support Agent with Live Trajectory Intelligence</h1>
        </div>
        <div className="topbar-stats">
          <span><MessageSquareText size={16} />chat-first support</span>
          <span><Bot size={16} />agentic workflow</span>
          <span><GitBranch size={16} />trajectory traces</span>
          <span><ShieldCheck size={16} />policy-safe actions</span>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="kpi-strip">
        <article>
          <span><TrendingUp size={15} />Resolution quality</span>
          <strong>{run ? `${run.evaluation.metrics.overall_score}/100` : "--"}</strong>
        </article>
        <article>
          <span><ShieldCheck size={15} />Blocked unsafe actions</span>
          <strong>{run ? policyGates : "--"}</strong>
        </article>
        <article>
          <span><AlertTriangle size={15} />Escalation rate</span>
          <strong>{run ? `${escalationRate}%` : "--"}</strong>
        </article>
        <article>
          <span><Clock3 size={15} />Handling time</span>
          <strong>{run ? `${totalLatency} ms` : "--"}</strong>
        </article>
        <article>
          <span><MessageSquareText size={15} />Customer tone</span>
          <strong>{run ? `${customerTone}%` : "--"}</strong>
        </article>
      </section>

      <section className="agent-cockpit">
        <div className="cockpit-column chat-column">
          <div className="column-label">
            <p className="eyebrow">Customer</p>
            <h2>Live support conversation</h2>
          </div>
          <CustomerAgentWorkspace tickets={tickets} run={run} isRunning={isRunning} onSubmit={handleCustomerQuery} />
        </div>

        <div className="cockpit-column workflow-column">
          <div className="column-label">
            <p className="eyebrow">Agent Workflow</p>
            <h2>Intent, retrieval, tools, policy, draft</h2>
            <p>{lastQuery || "Run a customer query to watch the support workflow unfold."}</p>
          </div>
          <TrajectoryTimeline spans={run?.trajectory ?? []} />
          <ToolTracePanel spans={run?.trajectory ?? []} />
        </div>

        <aside className="cockpit-column intelligence-column">
          <div className="column-label">
            <p className="eyebrow">Trajectory Intelligence</p>
            <h2>Evidence, governance, confidence</h2>
          </div>
          <PolicyGuardrailPanel run={run} />
          <EvaluationScorecard metrics={run?.evaluation.metrics} />
          <VisualEvidencePanel cards={run?.visual_evidence_cards ?? []} />
        </aside>
      </section>

      <section className="resolution-band">
        <div>
          <p className="eyebrow">Resolution</p>
          <h2>Safe support answer backed by citations</h2>
          <p>{run ? `${evidenceUsed} evidence references used across ${run.final_actions.length} drafted action(s).` : "The final answer appears after the agent handles a customer request."}</p>
        </div>
        <FinalActions actions={run?.final_actions ?? []} />
      </section>

      <details className="debug-drawer" open>
        <summary>
          <span>Replay and improvement console</span>
          <small>raw spans, observations, diagnosis, optimizer recommendations</small>
        </summary>
        <div className="debug-grid">
          <TraceViewer spans={run?.trajectory ?? []} />
          <FailureDiagnosis diagnosis={run?.evaluation.diagnosis ?? []} />
          <OptimizationPanel recommendations={run?.evaluation.recommendations ?? []} />
          <TicketQueue tickets={tickets} selectedTicketIds={selectedTicketIds} />
        </div>
      </details>

      <div className="demo-shortcut">
        <button className="secondary-button" onClick={handleLoadCustomerSupportDemo} disabled={isRunning}>
          Load full support demo queue
        </button>
      </div>
    </main>
  );
}
