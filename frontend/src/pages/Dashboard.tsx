import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUp,
  BookOpen,
  Bot,
  BrainCircuit,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  Database,
  Gauge,
  GitBranch,
  LoaderCircle,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  UserRoundCheck,
  Wrench
} from "lucide-react";
import {
  fetchCustomerSupportTickets,
  fetchKbLayers,
  fetchMemoryStatus,
  fetchRuntimeReadiness,
  fetchVectorStatus,
  resumeActiveSupportRun,
  runSupportAgentWithProgress
} from "../api/client";
import type { RunJobState } from "../api/client";
import type { KbLayerSummary, MemoryStatus, RunResult, RuntimeReadiness, SupportTicket, TrajectorySpan, VectorStatus } from "../api/types";

type View = "agent" | "intelligence";

const prompts = [
  "My withdrawal says processed, but the bank has not received it after five working days.",
  "My account is restricted for KYC. Unblock it so I can withdraw today.",
  "I made a UPI deposit yesterday and it is still not visible."
];

const executionPlan = [
  "Planner", "Attachment evidence", "Triage", "Knowledge retrieval", "Policy check", "Escalation",
  "Response drafting", "Compliance", "Human handoff", "Critic", "Reflection", "Learning", "Optimizer"
];

function formatLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function compactAgentName(name: string) {
  return name.replace(" Agent", "").replace("Intake / ", "").replace("Critic / Evaluator", "Critic");
}

function confidenceTone(value: number) {
  if (value >= 0.85) return "good";
  if (value >= 0.65) return "warn";
  return "risk";
}

export default function Dashboard() {
  const [view, setView] = useState<View>("agent");
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedTicketIds, setSelectedTicketIds] = useState<string[]>([]);
  const [run, setRun] = useState<RunResult | null>(null);
  const [prompt, setPrompt] = useState("");
  const [submittedPrompt, setSubmittedPrompt] = useState<string | null>(null);
  const [quickReply, setQuickReply] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [jobState, setJobState] = useState<RunJobState | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [vectorStatus, setVectorStatus] = useState<VectorStatus | null>(null);
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | null>(null);
  const [kbStatus, setKbStatus] = useState<KbLayerSummary | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeReadiness | null>(null);

  async function loadRuntime() {
    setIsBooting(true);
    setError(null);
    const [ticketResult, vectorResult, memoryResult, kbResult, runtimeResult] = await Promise.allSettled([
      fetchCustomerSupportTickets(),
      fetchVectorStatus(),
      fetchMemoryStatus(),
      fetchKbLayers(),
      fetchRuntimeReadiness()
    ]);

    if (ticketResult.status === "fulfilled") {
      setTickets(ticketResult.value);
      setSelectedTicketIds((current) => current.length ? current : ticketResult.value.slice(0, 1).map((ticket) => ticket.ticket_id));
    } else {
      setError(ticketResult.reason instanceof Error ? ticketResult.reason.message : "Unable to load the support queue.");
    }
    if (vectorResult.status === "fulfilled") setVectorStatus(vectorResult.value);
    if (memoryResult.status === "fulfilled") setMemoryStatus(memoryResult.value);
    if (kbResult.status === "fulfilled") setKbStatus(kbResult.value);
    if (runtimeResult.status === "fulfilled") setRuntimeStatus(runtimeResult.value);
    try {
      const resumed = await resumeActiveSupportRun((job) => {
        setJobState(job);
        setIsRunning(job.status === "queued" || job.status === "running");
      });
      if (resumed) {
        setRun(resumed);
        setSelectedTicketIds(resumed.selected_ticket_ids);
        setSubmittedPrompt(String(resumed.metadata.customer_query ?? "Resumed customer request"));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to resume the active agent run.");
    } finally {
      setIsRunning(false);
      setIsBooting(false);
    }
  }

  useEffect(() => {
    void loadRuntime();
  }, []);

  useEffect(() => {
    if (!isRunning) return;
    const timer = window.setInterval(() => setElapsed((current) => current + 1), 1000);
    return () => window.clearInterval(timer);
  }, [isRunning]);

  const selectedTickets = useMemo(
    () => tickets.filter((ticket) => selectedTicketIds.includes(ticket.ticket_id)),
    [tickets, selectedTicketIds]
  );
  const primaryAction = run?.final_actions[0] ?? null;
  const modelName = String(run?.metadata.model_name ?? runtimeStatus?.model_id ?? "runtime pending");
  const provider = String(run?.metadata.llm_provider ?? runtimeStatus?.provider ?? "connecting");
  const evidenceCount = new Set(run?.trajectory.flatMap((span) => span.evidence_ids) ?? []).size;
  const toolCount = run?.trajectory.reduce((total, span) => total + span.tools_used.length, 0) ?? 0;
  const riskCount = new Set(run?.trajectory.flatMap((span) => span.risk_flags) ?? []).size;

  async function execute() {
    const ids = selectedTicketIds.length ? selectedTicketIds : tickets.slice(0, 1).map((ticket) => ticket.ticket_id);
    if (!ids.length || !prompt.trim()) return;
    if (/^(hi|hello|hey|good morning|good afternoon|good evening)[!.\s]*$/i.test(prompt.trim())) {
      setSubmittedPrompt(prompt.trim());
      setQuickReply("Hi — I’m ready to investigate a customer-support case. Describe the payment, verification, account-access, or policy issue and I’ll trace the evidence, tools, approvals, and resolution path.");
      setRun(null);
      setJobState(null);
      setPrompt("");
      setError(null);
      return;
    }
    const customerPrompt = prompt.trim();
    setSubmittedPrompt(customerPrompt);
    setQuickReply(null);
    setRun(null);
    setJobState(null);
    setIsRunning(true);
    setElapsed(0);
    setError(null);
    setPrompt("");
    try {
      const result = await runSupportAgentWithProgress(ids, customerPrompt, setJobState);
      setRun(result);
      setSelectedTicketIds(result.selected_ticket_ids);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The agent run failed.");
    } finally {
      setIsRunning(false);
    }
  }

  function toggleTicket(id: string) {
    setSelectedTicketIds([id]);
  }

  function choosePrompt(item: string, index: number) {
    const matchingTicketIds = ["CS-002", "CS-003", "CS-001"];
    setPrompt(item);
    setSelectedTicketIds([matchingTicketIds[index]]);
  }

  return (
    <main className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-mark"><Sparkles size={18} /><span>Anirvium</span></div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <button className={view === "agent" ? "active" : ""} onClick={() => setView("agent")}>
            <Bot size={17} /><span>Support agent</span>
          </button>
          <button className={view === "intelligence" ? "active" : ""} onClick={() => setView("intelligence")}>
            <BrainCircuit size={17} /><span>Trajectory intelligence</span>
          </button>
        </nav>

        <div className="sidebar-section">
          <div className="sidebar-label"><span>Active queue</span><small>{selectedTicketIds.length}/{tickets.length}</small></div>
          <div className="case-list">
            {tickets.map((ticket) => (
              <button key={ticket.ticket_id} className={selectedTicketIds.includes(ticket.ticket_id) ? "selected" : ""} onClick={() => toggleTicket(ticket.ticket_id)}>
                <span className={`priority-dot ${ticket.priority}`} />
                <span><strong>{ticket.ticket_id}</strong><small>{formatLabel(ticket.issue_type)}</small></span>
                {selectedTicketIds.includes(ticket.ticket_id) && <Check size={14} />}
              </button>
            ))}
          </div>
        </div>

        <div className="runtime-card">
          <div><span className={`status-light ${error || runtimeStatus?.model_ready === false ? "error" : "online"}`} /><strong>{isBooting ? "Checking runtime" : error ? "Runtime issue" : runtimeStatus?.model_ready ? "AMD model ready" : "Model degraded"}</strong></div>
          <dl>
            <div><dt>Provider</dt><dd>{provider}</dd></div>
            <div><dt>Model</dt><dd title={modelName}>{modelName}</dd></div>
            <div><dt>Vector</dt><dd>{vectorStatus?.backend ?? "checking"}</dd></div>
          </dl>
        </div>
      </aside>

      <section className="product-area">
        <header className="product-header">
          <div>
            <span className="product-kicker">{view === "agent" ? "Customer support" : "Continuous improvement"}</span>
            <h1>{view === "agent" ? "Resolve with evidence, not guesswork." : "See how the agent thinks—and make it better."}</h1>
          </div>
          <div className="header-actions">
            <span className="run-identity"><Activity size={14} />{run?.run_id?.slice(-12) ?? "No active run"}</span>
            <button className="icon-button" onClick={() => void loadRuntime()} disabled={isRunning || isBooting} title="Refresh runtime status"><RefreshCw size={16} /></button>
          </div>
        </header>

        {error && (
          <div className="system-error"><CircleAlert size={17} /><span>{error}</span><button onClick={() => void loadRuntime()}>Reconnect</button></div>
        )}

        {view === "agent" ? (
          <AgentWorkspace
            prompt={prompt}
            setPrompt={setPrompt}
            run={run}
            primaryAction={primaryAction}
            quickReply={quickReply}
            submittedPrompt={submittedPrompt}
            selectedTickets={selectedTickets}
            isRunning={isRunning}
            isBooting={isBooting}
            jobState={jobState}
            elapsed={elapsed}
            onChoosePrompt={choosePrompt}
            onExecute={() => void execute()}
          />
        ) : (
          <IntelligenceWorkspace run={run} vectorStatus={vectorStatus} memoryStatus={memoryStatus} kbStatus={kbStatus} />
        )}
      </section>

      <ExecutionRail run={run} isRunning={isRunning} jobState={jobState} elapsed={elapsed} evidenceCount={evidenceCount} toolCount={toolCount} riskCount={riskCount} />
    </main>
  );
}

interface AgentWorkspaceProps {
  prompt: string;
  setPrompt: (value: string) => void;
  run: RunResult | null;
  primaryAction: RunResult["final_actions"][number] | null;
  quickReply: string | null;
  submittedPrompt: string | null;
  selectedTickets: SupportTicket[];
  isRunning: boolean;
  isBooting: boolean;
  jobState: RunJobState | null;
  elapsed: number;
  onChoosePrompt: (item: string, index: number) => void;
  onExecute: () => void;
}

function AgentWorkspace({ prompt, setPrompt, run, primaryAction, quickReply, submittedPrompt, selectedTickets, isRunning, isBooting, jobState, elapsed, onChoosePrompt, onExecute }: AgentWorkspaceProps) {
  return (
    <div className="agent-workspace">
      <section className="conversation-stream">
        <div className="context-line">
          <div className="context-avatars">{selectedTickets.slice(0, 3).map((ticket) => <span key={ticket.ticket_id}>{ticket.ticket_id.slice(-1)}</span>)}</div>
          <span>{selectedTickets.length ? `${selectedTickets.length} selected support case${selectedTickets.length > 1 ? "s" : ""}` : "Select a case from the queue"}</span>
        </div>

        {submittedPrompt && <div className="user-turn"><span>{submittedPrompt}</span></div>}

        {isRunning ? (
          <article className="answer-card pending-answer">
            <div className="answer-meta">
              <div className="agent-avatar"><LoaderCircle className="spin" size={17} /></div>
              <div><strong>{jobState?.current_agent ?? "Anirvium Support Agent"}</strong><span>{jobState?.progress_message ?? "Connecting to the AMD agent runtime"}</span></div>
              <span className="approval-state safe">{jobState?.progress_percent ?? 0}%</span>
            </div>
            <div className="progress-track"><i style={{ width: `${jobState?.progress_percent ?? 2}%` }} /></div>
            <p className="answer-copy pending-copy">Investigating the request, retrieving governed evidence, and checking policy constraints. The job remains recoverable if the public AMD proxy briefly reconnects.</p>
          </article>
        ) : primaryAction || quickReply ? (
          <article className="answer-card">
            <div className="answer-meta">
              <div className="agent-avatar"><Sparkles size={17} /></div>
              <div><strong>Anirvium Support Agent</strong><span>Evidence-grounded resolution</span></div>
              <span className={`approval-state ${primaryAction?.approval_state === "APPROVAL_REQUIRED" ? "review" : "safe"}`}>
                {primaryAction?.approval_state === "APPROVAL_REQUIRED" ? <UserRoundCheck size={13} /> : <ShieldCheck size={13} />}
                {quickReply ? "Ready" : formatLabel(primaryAction?.approval_state ?? "ready")}
              </span>
            </div>
            <p className="answer-copy">{quickReply ?? primaryAction?.draft_response}</p>
            {primaryAction && !quickReply && <>
              <div className="answer-details">
                <span><Gauge size={14} />{Math.round((primaryAction.confidence_score ?? 0) * 100)}% confidence</span>
                <span><BookOpen size={14} />{primaryAction.evidence_ids.length} sources</span>
                <span><UserRoundCheck size={14} />{primaryAction.owner}</span>
                <span><Sparkles size={14} />{primaryAction.generation_source === "amd_vllm" ? primaryAction.generation_model ?? "AMD vLLM" : "Verified safe fallback"}</span>
              </div>
              <div className="source-row">{primaryAction.evidence_ids.map((id) => <span key={id}>{id}</span>)}</div>
            </>}
          </article>
        ) : (
          <div className="empty-answer"><BrainCircuit size={32} /><strong>Ready to investigate</strong><span>Select a case and describe the customer problem.</span></div>
        )}

        {run && !isRunning && (
          <div className="resolution-summary">
            <span><ShieldCheck size={15} />Policy checked</span>
            <span><Search size={15} />Evidence grounded</span>
            <span><GitBranch size={15} />{run.trajectory.length} decisions traced</span>
          </div>
        )}
      </section>

      <section className="composer-zone">
        {isRunning && (
          <div className="execution-notice"><LoaderCircle className="spin" size={16} /><span>{jobState?.current_agent ?? "AMD agent runtime is starting"}</span><strong>{elapsed}s</strong><small>Step {jobState?.current_step ?? 0} of {jobState?.total_steps ?? 13}</small></div>
        )}
        <div className="suggestion-row">
          {prompts.map((item, index) => <button key={item} onClick={() => onChoosePrompt(item, index)}>{index === 0 ? "Withdrawal delay" : index === 1 ? "KYC restriction" : "Missing deposit"}</button>)}
        </div>
        <div className={`prompt-composer ${isRunning ? "processing" : ""}`}>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Describe the customer issue…" rows={3} />
          <div className="composer-footer">
            <div><span><Database size={14} />Knowledge base</span><span><ShieldCheck size={14} />Policy guardrails</span></div>
            <button onClick={onExecute} disabled={isRunning || isBooting || !prompt.trim()} aria-label="Run support agent">
              {isRunning || isBooting ? <LoaderCircle className="spin" size={18} /> : <ArrowUp size={18} />}
            </button>
          </div>
        </div>
        <p className="composer-caption">Responses are drafts until policy and approval checks complete.</p>
      </section>
    </div>
  );
}

function ExecutionRail({ run, isRunning, jobState, elapsed, evidenceCount, toolCount, riskCount }: { run: RunResult | null; isRunning: boolean; jobState: RunJobState | null; elapsed: number; evidenceCount: number; toolCount: number; riskCount: number }) {
  const spans = run?.trajectory ?? [];
  return (
    <aside className="execution-rail">
      <div className="rail-header">
        <div><span className="product-kicker">Live execution</span><h2>Agent trajectory</h2></div>
        <span className={`live-indicator ${isRunning ? "running" : ""}`}><span />{isRunning ? `${elapsed}s` : "complete"}</span>
      </div>
      <div className="rail-stats">
        <div><strong>{spans.length}</strong><span>steps</span></div>
        <div><strong>{toolCount}</strong><span>tools</span></div>
        <div><strong>{evidenceCount}</strong><span>evidence</span></div>
        <div><strong>{riskCount}</strong><span>risks</span></div>
      </div>
      <div className="trajectory-list">
        {isRunning ? executionPlan.map((name, index) => {
          const step = index + 1;
          const currentStep = jobState?.current_step ?? 0;
          const state = step < currentStep ? "completed" : step === currentStep ? "active" : "pending";
          return (
            <div className={`trajectory-step pending ${state}`} key={name}>
              <span className={`step-node ${state === "completed" ? "good" : ""}`}>{state === "completed" ? <Check size={12} /> : step}</span>
              <div><strong>{name}</strong><small>{state === "completed" ? "Completed" : state === "active" ? "Executing on AMD runtime" : "Waiting for structured context"}</small></div>
              {state === "active" && <LoaderCircle className="spin" size={14} />}
            </div>
          );
        }) : spans.map((span, index) => <TrajectoryStep span={span} index={index} key={span.step_id} />)}
      </div>
      {!isRunning && spans.length > 0 && <div className="rail-complete"><Check size={15} /><span>Trajectory captured and evaluated</span></div>}
    </aside>
  );
}

function TrajectoryStep({ span, index }: { span: TrajectorySpan; index: number }) {
  return (
    <details className="trajectory-step">
      <summary>
        <span className={`step-node ${confidenceTone(span.confidence)}`}>{index + 1}</span>
        <div><strong>{compactAgentName(span.agent_name)}</strong><small>{span.latency_ms}ms · {Math.round(span.confidence * 100)}% confidence</small></div>
        <ChevronDown size={14} />
      </summary>
      <div className="step-detail">
        <p>{span.reasoning_summary || span.output_summary}</p>
        <div>{span.tools_used.map((tool) => <span key={tool}><Wrench size={11} />{tool}</span>)}</div>
        <div>{span.evidence_ids.slice(0, 4).map((id) => <span key={id}><BookOpen size={11} />{id}</span>)}</div>
      </div>
    </details>
  );
}

function IntelligenceWorkspace({ run, vectorStatus, memoryStatus, kbStatus }: { run: RunResult | null; vectorStatus: VectorStatus | null; memoryStatus: MemoryStatus | null; kbStatus: KbLayerSummary | null }) {
  const metrics = run?.evaluation.metrics;
  const metricRows = metrics ? [
    ["Evidence grounding", metrics.evidence_grounding],
    ["Policy compliance", metrics.policy_compliance],
    ["Escalation quality", metrics.escalation_quality],
    ["Actionability", metrics.actionability]
  ] as const : [];

  return (
    <div className="intelligence-workspace">
      <section className="intelligence-hero">
        <div className="health-orb"><span>{metrics?.overall_score ?? "--"}</span><small>trajectory health</small></div>
        <div><span className="product-kicker">Post-run intelligence</span><h2>The system observes every decision, then proposes how to improve it.</h2><p>{run?.evaluation.summary ?? "Run the support agent to generate trajectory intelligence."}</p></div>
      </section>

      <section className="metric-cards">
        {metricRows.map(([label, value]) => <article key={label}><span>{label}</span><strong>{Math.round(value * 100)}%</strong><div><i style={{ width: `${value * 100}%` }} /></div></article>)}
      </section>

      <section className="intelligence-grid">
        <article className="intelligence-panel">
          <header><CircleAlert size={17} /><div><strong>Failure signals</strong><span>What degraded this run</span></div><b>{run?.evaluation.diagnosis.length ?? 0}</b></header>
          <div className="insight-list">{run?.evaluation.diagnosis.slice(0, 4).map((item, index) => <div key={`${item.category}-${index}`}><span className={`severity ${item.severity.toLowerCase()}`}>{item.severity}</span><strong>{formatLabel(item.failure_type || item.category)}</strong><p>{item.message}</p><small>{item.affected_agent}</small></div>)}</div>
        </article>
        <article className="intelligence-panel accent">
          <header><BrainCircuit size={17} /><div><strong>Improvement plan</strong><span>Changes extracted from the trajectory</span></div><b>{run?.evaluation.recommendations.length ?? 0}</b></header>
          <div className="insight-list">{run?.evaluation.recommendations.slice(0, 4).map((item) => <div key={item.recommendation_id}><span className="severity improve">{item.priority}</span><strong>{item.title}</strong><p>{item.fix || item.rationale}</p><small>Target · {item.target_agent}</small></div>)}</div>
        </article>
      </section>

      <section className="infrastructure-strip">
        <div><Database size={17} /><span>Vector index</span><strong>{vectorStatus?.backend ?? "unknown"}</strong><small>{vectorStatus?.qdrant_reachable ? "Qdrant connected" : "Local fallback"}</small></div>
        <div><BookOpen size={17} /><span>Knowledge layers</span><strong>{kbStatus?.record_count ?? "--"}</strong><small>{kbStatus?.layer_count ?? 0} governed layers</small></div>
        <div><Network size={17} /><span>Trajectory graph</span><strong>{run?.graph.nodes.length ?? "--"}</strong><small>{run?.graph.edges.length ?? 0} relationships</small></div>
        <div><TerminalSquare size={17} /><span>Agent memory</span><strong>{memoryStatus?.memory_backend ?? "unknown"}</strong><small>{memoryStatus?.redis_reachable ? "Redis connected" : "Local fallback"}</small></div>
      </section>
    </div>
  );
}
