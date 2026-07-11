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
  processConversationTurn,
  resumeActiveSupportRun,
  runSupportAgentWithProgress,
  submitSatisfactionFeedback
} from "../api/client";
import type { RunJobState } from "../api/client";
import type { ConversationTurn, ExecutionMode, KbLayerSummary, MemoryStatus, RunResult, RuntimeReadiness, SupportTicket, TrajectorySpan, VectorStatus } from "../api/types";

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
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("hybrid");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [conversationKind, setConversationKind] = useState<string | null>(null);
  const [conversationTurns, setConversationTurns] = useState<ConversationTurn[]>([]);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [feedbackPending, setFeedbackPending] = useState(false);

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
        setConversationId(String(resumed.metadata.conversation_id ?? "") || undefined);
        setExecutionMode((resumed.metadata.execution_mode as ExecutionMode) ?? "hybrid");
        setConversationTurns(resumed.sarvagun?.transcript.turns ?? []);
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
    const customerPrompt = prompt.trim();
    setSubmittedPrompt(customerPrompt);
    setQuickReply(null);
    setRun(null);
    setJobState(null);
    setElapsed(0);
    setError(null);
    setPrompt("");
    setFeedbackSent(false);
    setFeedbackPending(false);
    setIsRunning(true);
    try {
      const turn = await processConversationTurn(customerPrompt, conversationId, selectedTickets[0]?.customer_id);
      setConversationId(turn.signal.conversation_id);
      setConversationKind(turn.signal.message_type);
      setConversationTurns(turn.turns);
      if (!turn.signal.requires_agent_run) {
        setQuickReply(turn.signal.response ?? "I’m ready to help with your support request.");
        return;
      }
      const result = await runSupportAgentWithProgress(
        ids,
        customerPrompt,
        setJobState,
        executionMode,
        turn.signal.conversation_id,
        selectedTickets[0]?.customer_id
      );
      setRun(result);
      setSelectedTicketIds(result.selected_ticket_ids);
      setConversationTurns(result.sarvagun?.transcript.turns ?? turn.turns);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The agent run failed.");
    } finally {
      setIsRunning(false);
    }
  }

  async function sendFeedback(rating: number, resolution: "yes" | "partially" | "no") {
    if (!run || feedbackPending || feedbackSent) return;
    setFeedbackPending(true);
    try {
      await submitSatisfactionFeedback(run.run_id, rating, resolution);
      setFeedbackSent(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to record satisfaction feedback.");
    } finally {
      setFeedbackPending(false);
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
          <button className={view === "agent" ? "active" : ""} onClick={() => setView("agent")} aria-current={view === "agent" ? "page" : undefined}>
            <Bot size={17} /><span>Sarvagun</span>
          </button>
          <button className={view === "intelligence" ? "active" : ""} onClick={() => setView("intelligence")} aria-current={view === "intelligence" ? "page" : undefined}>
            <BrainCircuit size={17} /><span>SuperTuriya</span>
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
            <span className="product-kicker">{view === "agent" ? "Sarvagun customer support" : "SuperTuriya intelligence"}</span>
            <h1>{view === "agent" ? "Resolve with evidence, empathy, and governed action." : "See why Sarvagun acted—and how SuperTuriya improves it."}</h1>
          </div>
          <div className="header-actions">
            <span className="run-identity"><Activity size={14} />{run?.run_id?.slice(-12) ?? "No active run"}</span>
            <button className="icon-button" onClick={() => void loadRuntime()} disabled={isRunning || isBooting} title="Refresh runtime status"><RefreshCw size={16} /></button>
          </div>
        </header>

        {error && (
          <div className="system-error" role="alert"><CircleAlert size={17} /><span>{error}</span><button onClick={() => void loadRuntime()}>Reconnect</button></div>
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
            executionMode={executionMode}
            setExecutionMode={setExecutionMode}
            conversationKind={conversationKind}
            conversationTurns={conversationTurns}
            feedbackSent={feedbackSent}
            feedbackPending={feedbackPending}
            elapsed={elapsed}
            onChoosePrompt={choosePrompt}
            onFeedback={(rating, resolution) => void sendFeedback(rating, resolution)}
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
  executionMode: ExecutionMode;
  setExecutionMode: (mode: ExecutionMode) => void;
  conversationKind: string | null;
  conversationTurns: ConversationTurn[];
  feedbackSent: boolean;
  feedbackPending: boolean;
  elapsed: number;
  onChoosePrompt: (item: string, index: number) => void;
  onFeedback: (rating: number, resolution: "yes" | "partially" | "no") => void;
  onExecute: () => void;
}

function AgentWorkspace({ prompt, setPrompt, run, primaryAction, quickReply, submittedPrompt, selectedTickets, isRunning, isBooting, jobState, executionMode, setExecutionMode, conversationKind, conversationTurns, feedbackSent, feedbackPending, elapsed, onChoosePrompt, onFeedback, onExecute }: AgentWorkspaceProps) {
  const [resolutionFeedback, setResolutionFeedback] = useState<"yes" | "partially" | "no">("partially");
  const [submittedRating, setSubmittedRating] = useState<number | null>(null);
  const cx = run?.sarvagun;
  const historyTurns = useMemo(() => {
    let end = conversationTurns.length;
    const latest = conversationTurns[end - 1];
    if (latest?.role === "agent" && (latest.content === quickReply || latest.content === primaryAction?.draft_response)) end -= 1;
    const latestCustomer = conversationTurns[end - 1];
    if (latestCustomer?.role === "customer" && latestCustomer.content === submittedPrompt) end -= 1;
    return conversationTurns.slice(0, end);
  }, [conversationTurns, primaryAction?.draft_response, quickReply, submittedPrompt]);

  useEffect(() => {
    setSubmittedRating(null);
    setResolutionFeedback("partially");
  }, [run?.run_id]);

  function submitFeedback(rating: number) {
    setSubmittedRating(rating);
    onFeedback(rating, resolutionFeedback);
  }

  return (
    <div className="agent-workspace">
      <section className="conversation-stream">
        <div className="context-line">
          <div className="context-avatars">{selectedTickets.slice(0, 3).map((ticket) => <span key={ticket.ticket_id}>{ticket.ticket_id.slice(-1)}</span>)}</div>
          <span>{selectedTickets.length ? `${selectedTickets.length} selected support case${selectedTickets.length > 1 ? "s" : ""}` : "Select a case from the queue"}</span>
          {conversationKind && <small className="context-classification">{formatLabel(conversationKind)}</small>}
        </div>

        {historyTurns.length > 0 && (
          <div className="conversation-history" aria-label="Earlier conversation turns">
            {historyTurns.map((turn) => turn.role === "customer" ? (
              <div className="user-turn prior-turn" key={turn.turn_id}><span>{turn.content}</span></div>
            ) : turn.role === "agent" ? (
              <div className="agent-history-turn" key={turn.turn_id}><Sparkles size={14} /><p>{turn.content}</p></div>
            ) : null)}
          </div>
        )}

        {submittedPrompt && <div className="user-turn"><span>{submittedPrompt}</span></div>}

        {isRunning ? (
          <article className="answer-card pending-answer" aria-busy="true" aria-live="polite">
            <div className="answer-meta">
              <div className="agent-avatar"><LoaderCircle className="spin" size={17} /></div>
              <div><strong>{jobState?.current_agent ?? "Sarvagun"}</strong><span>{jobState?.progress_message ?? "Connecting to the AMD agent runtime"}</span></div>
              <span className="approval-state safe">{jobState?.progress_percent ?? 0}%</span>
            </div>
            <div className="progress-track" role="progressbar" aria-label="Sarvagun execution progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={jobState?.progress_percent ?? 0}><i style={{ width: `${jobState?.progress_percent ?? 2}%` }} /></div>
            <p className="answer-copy pending-copy">Investigating the request, retrieving governed evidence, and checking policy constraints. The job remains recoverable if the public AMD proxy briefly reconnects.</p>
          </article>
        ) : primaryAction || quickReply ? (
          <article className="answer-card">
            <div className="answer-meta">
              <div className="agent-avatar"><Sparkles size={17} /></div>
              <div><strong>Sarvagun</strong><span>Governed customer-support execution</span></div>
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
                {cx && <span><ShieldCheck size={14} />SuperTuriya gate {Math.round(cx.response_quality_gate.score * 100)}% · {formatLabel(cx.response_quality_gate.decision)}</span>}
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
            {cx && <span><UserRoundCheck size={15} />{formatLabel(cx.response_quality_gate.decision)}</span>}
            <span><GitBranch size={15} />{run.trajectory.length} decisions traced</span>
          </div>
        )}

        {cx && !isRunning && (
          <>
            {cx.incident.detected && (
              <div className="incident-alert"><CircleAlert size={17} /><div><strong>Emerging issue detected</strong><span>{cx.incident.unique_customers} unique customers affected in {cx.incident.window_minutes} minutes · {formatLabel(cx.incident.recommended_action)}</span></div></div>
            )}
            <section className="cx-signal-grid" aria-label="Sarvagun customer experience signals">
              <article><span>Emotion</span><strong>{formatLabel(cx.emotion.primary_emotion)}</strong><small>{Math.round(cx.emotion.intensity * 100)}% intensity</small></article>
              <article><span>Recontact</span><strong>{cx.recontact.recontact_detected ? "Detected" : "First contact"}</strong><small>{cx.recontact.contacts_last_7_days} contacts · 7 days</small></article>
              <article><span>Escalation</span><strong>{formatLabel(cx.escalation.status)}</strong><small>{formatLabel(cx.escalation.destination)} · {cx.escalation.sla_minutes}m SLA</small></article>
              <article><span>AI-predicted satisfaction</span><strong>{Math.round(cx.satisfaction.predicted_satisfaction * 100)}%</strong><small>{formatLabel(cx.satisfaction.predicted_label)} · not actual CSAT</small></article>
            </section>
            <details className="provenance-drawer">
              <summary><Wrench size={14} /><span>Evidence, enterprise tools, assurance, and transcript</span><ChevronDown size={14} /></summary>
              <div className="provenance-content">
                <div><strong>{cx.tool_executions.length} audited tool executions{cx.tool_executions.every((tool) => tool.simulated) ? " · mock connector" : ""}</strong><p>{cx.tool_executions.map((tool) => `${formatLabel(tool.tool_name)} / ${formatLabel(tool.operation)} · ${tool.status}${tool.simulated ? " · simulated" : ""}`).join("  |  ")}</p></div>
                <div><strong>Response provenance</strong><p>{cx.provenance[0]?.customer_view ?? "No customer-safe provenance summary was recorded."}</p>{cx.provenance[0]?.sources.length ? <p>{cx.provenance[0].sources.map((source) => `${source.source_id} · ${source.title} · ${source.version}`).join("  |  ")}</p> : null}</div>
                <div><strong>Assurance</strong><p>{cx.assurances[0]?.assurance_text ?? "No customer assurance was recorded."}</p></div>
                <div><strong>SuperTuriya response quality gate</strong><p>{Math.round(cx.response_quality_gate.score * 100)}% · {formatLabel(cx.response_quality_gate.decision)} · {Object.entries(cx.response_quality_gate.checks).filter(([, passed]) => passed).length}/{Object.keys(cx.response_quality_gate.checks).length} checks passed</p></div>
                <div><strong>Transcript</strong><p>{cx.transcript.transcript_id} · {cx.transcript.turns.length} recorded turns · {cx.transcript.redaction_status}</p></div>
              </div>
            </details>
            <section className="satisfaction-tray" aria-label="Explicit customer satisfaction">
              <div><strong>Was the issue resolved?</strong><span>Actual customer feedback remains separate from AI prediction.</span></div>
              <div className="resolution-options">
                {(["yes", "partially", "no"] as const).map((value) => <button className={resolutionFeedback === value ? "active" : ""} key={value} onClick={() => setResolutionFeedback(value)} disabled={feedbackSent || feedbackPending} aria-pressed={resolutionFeedback === value}>{formatLabel(value)}</button>)}
              </div>
              <div className="rating-options" aria-label="Rate support from one to five">
                {feedbackSent ? <span className="feedback-confirmation"><Check size={13} />{submittedRating}/5 recorded</span> : [1, 2, 3, 4, 5].map((rating) => <button key={rating} disabled={feedbackPending} onClick={() => submitFeedback(rating)} aria-label={`${rating} out of 5`}>{feedbackPending && submittedRating === rating ? <LoaderCircle className="spin" size={13} /> : rating}</button>)}
              </div>
            </section>
          </>
        )}
      </section>

      <section className="composer-zone">
        {isRunning && (
          <div className="execution-notice" aria-live="polite"><LoaderCircle className="spin" size={16} /><span>{jobState?.current_agent ?? "Sarvagun conversation manager is classifying the turn"}</span><strong>{elapsed}s</strong><small>Step {jobState?.current_step ?? 0} of {jobState?.total_steps ?? 13}</small></div>
        )}
        <div className="suggestion-row">
          {prompts.map((item, index) => <button key={item} onClick={() => onChoosePrompt(item, index)}>{index === 0 ? "Withdrawal delay" : index === 1 ? "KYC restriction" : "Missing deposit"}</button>)}
        </div>
        <div className={`prompt-composer ${isRunning ? "processing" : ""}`}>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && prompt.trim() && !isRunning && !isBooting) {
                event.preventDefault();
                onExecute();
              }
            }}
            aria-label="Customer support message"
            placeholder="Describe the customer issue…"
            rows={3}
            disabled={isRunning || isBooting}
          />
          <div className="composer-footer">
            <div><span><Database size={14} />Knowledge base</span><span><ShieldCheck size={14} />Policy guardrails</span>
              <label className="mode-control">Mode
                <select value={executionMode} onChange={(event) => setExecutionMode(event.target.value as ExecutionMode)} disabled={isRunning}>
                  <option value="policy_driven">Policy guided</option>
                  <option value="plan_driven">Plan guided</option>
                  <option value="autonomous">Bounded autonomous</option>
                  <option value="hybrid">Hybrid governed</option>
                </select>
              </label>
            </div>
            <button onClick={onExecute} disabled={isRunning || isBooting || !prompt.trim()} aria-label="Run Sarvagun">
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
  const stateLabel = isRunning ? `${elapsed}s` : spans.length > 0 ? "complete" : "idle";
  return (
    <aside className="execution-rail">
      <div className="rail-header">
        <div><span className="product-kicker">Sarvagun execution</span><h2>Live trajectory · SuperTuriya observing</h2></div>
        <span className={`live-indicator ${isRunning ? "running" : spans.length > 0 ? "complete" : "idle"}`}><span />{stateLabel}</span>
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
              <div><strong>{name}</strong><small>{index < 9 ? "Sarvagun" : "SuperTuriya"} · {state === "completed" ? "Completed" : state === "active" ? "Executing on AMD runtime" : "Waiting for structured context"}</small></div>
              {state === "active" && <LoaderCircle className="spin" size={14} />}
            </div>
          );
        }) : spans.map((span, index) => <TrajectoryStep span={span} index={index} key={span.step_id} />)}
      </div>
      {!isRunning && spans.length > 0 && <div className="rail-complete"><Check size={15} /><span>SuperTuriya captured, evaluated, and stored the trajectory</span></div>}
    </aside>
  );
}

function TrajectoryStep({ span, index }: { span: TrajectorySpan; index: number }) {
  return (
    <details className="trajectory-step">
      <summary>
        <span className={`step-node ${confidenceTone(span.confidence)}`}>{index + 1}</span>
        <div><strong>{compactAgentName(span.agent_name)}</strong><small>{index < 9 ? "Sarvagun" : "SuperTuriya"} · {span.latency_ms}ms · {Math.round(span.confidence * 100)}% confidence</small></div>
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
  const cx = run?.sarvagun;
  const intelligence = run?.superturiya;
  const metricRows: Array<readonly [string, number]> = metrics ? [
    ["Evidence grounding", metrics.evidence_grounding],
    ["Policy compliance", metrics.policy_compliance],
    ["CX response quality", cx?.satisfaction.rubric.overall_quality ?? metrics.customer_tone],
    cx ? ["AI-predicted satisfaction", cx.satisfaction.predicted_satisfaction] : ["Actionability", metrics.actionability]
  ] : [];

  return (
    <div className="intelligence-workspace">
      <section className="intelligence-hero">
        <div className="health-orb"><span>{metrics?.overall_score ?? "--"}</span><small>trajectory health</small></div>
        <div><span className="product-kicker">SuperTuriya intelligence</span><h2>SuperTuriya observes Sarvagun, discovers its path, evaluates the outcome, and closes the memory loop.</h2><p>{run?.evaluation.summary ?? "Run Sarvagun to generate trajectory intelligence."}</p></div>
      </section>

      <section className="metric-cards">
        {metricRows.map(([label, value]) => <article key={label}><span>{label}</span><strong>{Math.round(value * 100)}%</strong><div><i style={{ width: `${value * 100}%` }} /></div></article>)}
      </section>

      {intelligence ? (
        <section className="superturiya-loop">
          <div><span className="product-kicker">{formatLabel(intelligence.feedback_loop_status)} intelligence loop</span><strong>Sarvagun executes → SuperTuriya observes → evaluates → discovers → remembers → improves the next plan</strong></div>
          <div className="loop-stats">
            <span><b>{intelligence.event_count}</b> events observed</span>
            <span><b>{intelligence.recalled_memory_ids.length}</b> memories recalled</span>
            <span><b>{intelligence.applied_memory_ids.length}</b> plan influences</span>
            <span><b>{intelligence.created_memory_ids.length}</b> memories created</span>
          </div>
          <p>{intelligence.lifecycle.map(formatLabel).join(" → ")} · Automatic policy mutation is {intelligence.automatic_policy_mutation ? "enabled" : "disabled for safety"}.</p>
        </section>
      ) : (
        <section className="superturiya-loop awaiting-loop"><span className="product-kicker">Intelligence loop idle</span><strong>Run Sarvagun to let SuperTuriya observe, evaluate, and store a trajectory.</strong></section>
      )}

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
        <div><TerminalSquare size={17} /><span>SuperTuriya memory</span><strong>{memoryStatus?.memory_backend ?? "unknown"}</strong><small>{memoryStatus?.redis_reachable ? "Redis operational memory" : "Local operational fallback"}</small></div>
      </section>
    </div>
  );
}
