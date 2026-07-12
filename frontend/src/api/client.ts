import type {
  CustomerSupportDemoResponse,
  CaseContext,
  ConversationTurnResponse,
  ExecutionMode,
  KbLayerSummary,
  KbSearchResponse,
  MemoryStatus,
  RuntimeReadiness,
  RunResult,
  SupportTicket,
  VectorStatus,
  WinningDemoResponse
} from "./types";

// Keep browser traffic on the frontend origin by default. Vite proxies `/api`
// during local development and Nginx proxies it in the Docker image. This
// avoids hard-coding localhost in the browser, which breaks remote and hosted
// demos because localhost always means the judge's own machine.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "api").replace(/\/$/, "");
const ACTIVE_JOB_KEY = "anirvium.active-run-job";
const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === "true";
const STATIC_ROOT = `${import.meta.env.BASE_URL}static`;

async function loadStaticJson<T>(name: string): Promise<T> {
  const response = await fetch(`${STATIC_ROOT}/${name}`);
  if (!response.ok) throw new Error(`Static judge artifact ${name} is unavailable.`);
  return response.json() as Promise<T>;
}

function staticJob(run: RunResult): RunJobState {
  return {
    job_id: `static-${run.run_id}`,
    status: "completed",
    current_step: run.trajectory.length,
    total_steps: run.trajectory.length,
    current_agent: null,
    progress_percent: 100,
    progress_message: "Precomputed synthetic trajectory loaded",
    result: run,
    error: null
  };
}

export interface RunJobState {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_step: number;
  total_steps: number;
  current_agent: string | null;
  progress_percent: number;
  progress_message: string | null;
  result: RunResult | null;
  error: string | null;
}

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly statusText: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method ?? "GET";
  const startedAt = performance.now();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 300_000);
  console.info(`[Anirvium API] ${method} ${path} started`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {})
      },
      signal: options?.signal ?? controller.signal
    });
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - startedAt);
    console.error(`[Anirvium API] ${method} ${path} failed after ${elapsedMs}ms`, error);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The AMD run exceeded five minutes. Inspect FastAPI and vLLM logs before retrying.");
    }
    throw new Error("Backend unavailable. Verify the frontend /api proxy and FastAPI health endpoint.");
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    console.error(`[Anirvium API] ${method} ${path} returned ${response.status}`);
    let detail = "";
    try {
      const payload = await response.json() as { detail?: string };
      detail = payload.detail ? `: ${payload.detail}` : "";
    } catch {
      // Some upstream AMD proxy errors return HTML rather than JSON.
    }
    throw new ApiError(`${response.status} ${response.statusText}${detail}`, response.status, response.statusText);
  }

  console.info(
    `[Anirvium API] ${method} ${path} completed in ${Math.round(performance.now() - startedAt)}ms`,
    {
      requestId: response.headers.get("x-request-id"),
      correlationId: response.headers.get("x-correlation-id")
    }
  );

  return response.json() as Promise<T>;
}

export async function fetchTickets(): Promise<SupportTicket[]> {
  if (STATIC_DEMO) return loadStaticJson<SupportTicket[]>("customer_support_tickets.json");
  const payload = await request<{ tickets: SupportTicket[] }>("/tickets");
  return payload.tickets;
}

export async function fetchCustomerSupportTickets(): Promise<SupportTicket[]> {
  if (STATIC_DEMO) return loadStaticJson<SupportTicket[]>("customer_support_tickets.json");
  const payload = await request<{ tickets: SupportTicket[] }>("/tickets?dataset=customer_support");
  return payload.tickets;
}

export async function fetchCaseContext(caseId: string): Promise<CaseContext> {
  if (STATIC_DEMO) {
    const tickets = await loadStaticJson<SupportTicket[]>("customer_support_tickets.json");
    const ticket = tickets.find((item) => item.ticket_id === caseId);
    if (!ticket) throw new Error(`Synthetic case ${caseId} was not found.`);
    return {
      synthetic_data_only: true,
      case: { case_id: ticket.ticket_id, customer_id: ticket.customer_id, issue_type: ticket.issue_type, priority: ticket.priority, status: "OPEN" },
      customer: { customer_id: ticket.customer_id, customer_name: ticket.customer_name, plan: ticket.plan },
      accounts: [],
      transactions: [],
      verification_records: [],
      approval_requests: [],
      escalations: [],
      workflow_states: []
    };
  }
  return request<CaseContext>(`/data/cases/${encodeURIComponent(caseId)}/context`);
}

export async function runSupportAgent(selectedTicketIds?: string[], customerQuery?: string): Promise<RunResult> {
  if (STATIC_DEMO) {
    const caseId = selectedTicketIds?.[0] ?? "CS-002";
    return loadStaticJson<RunResult>(`run_${caseId}.json`);
  }
  const body = selectedTicketIds?.length
    ? { selection_mode: "selected", selected_ticket_ids: selectedTicketIds, dataset: "customer_support", customer_query: customerQuery, execution_mode: "hybrid" }
    : { selection_mode: "all_high_priority", dataset: "customer_support", execution_mode: "hybrid" };

  const job = await request<RunJobState>("/runs/async", {
    method: "POST",
    body: JSON.stringify(body)
  });

  persistActiveJob(job.job_id);
  return pollRunJob(job.job_id);
}

export async function runSupportAgentWithProgress(
  selectedTicketIds: string[] | undefined,
  customerQuery: string | undefined,
  onProgress: (job: RunJobState) => void,
  executionMode: ExecutionMode = "hybrid",
  conversationId?: string,
  customerId?: string,
  correlationId?: string
): Promise<RunResult> {
  if (STATIC_DEMO) {
    const caseId = selectedTicketIds?.[0] ?? "CS-002";
    const result = await loadStaticJson<RunResult>(`run_${caseId}.json`);
    onProgress({ ...staticJob(result), status: "running", current_step: 7, progress_percent: 54, progress_message: "Loading verified synthetic trajectory snapshot", result: null });
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    onProgress(staticJob(result));
    return result;
  }
  const body = selectedTicketIds?.length
    ? { selection_mode: "selected", selected_ticket_ids: selectedTicketIds, dataset: "customer_support", customer_query: customerQuery, execution_mode: executionMode, conversation_id: conversationId, customer_id: customerId }
    : { selection_mode: "all_high_priority", dataset: "customer_support", customer_query: customerQuery, execution_mode: executionMode, conversation_id: conversationId, customer_id: customerId };

  const job = await request<RunJobState>("/runs/async", {
    method: "POST",
    headers: correlationId ? { "X-Correlation-ID": correlationId } : undefined,
    body: JSON.stringify(body)
  });

  persistActiveJob(job.job_id);
  onProgress(job);
  return pollRunJob(job.job_id, onProgress);
}

export async function processConversationTurn(
  message: string,
  conversationId?: string,
  customerId?: string,
  correlationId?: string
): Promise<ConversationTurnResponse> {
  if (STATIC_DEMO) {
    const normalized = message.trim().toLowerCase();
    const id = conversationId ?? `static-conversation-${Date.now()}`;
    const now = new Date().toISOString();
    const tickets = await loadStaticJson<SupportTicket[]>("customer_support_tickets.json");
    const greeting = /^(hi|hello|hey)[!. ]*$/.test(normalized);
    const customerDirectory = normalized.includes("list all customers") || normalized.includes("show all customers");
    const paymentCases = normalized.includes("payment") && (normalized.includes("case") || normalized.includes("failure"));
    const generalKnowledge = normalized.includes("capital market");
    const quickReply = greeting
      ? "Hello. Select a synthetic support case or describe the customer issue and Sarvagun will route it."
      : generalKnowledge
        ? "A capital market is a market where long-term financial instruments such as shares and bonds are issued and traded. This static judge mode uses a precomputed answer; the live AMD path routes this request to Qwen3."
        : null;
    const records = customerDirectory
      ? tickets.map((ticket) => ({ customer_id: ticket.customer_id, customer_name: ticket.customer_name, plan: ticket.plan }))
      : paymentCases
        ? tickets.filter((ticket) => ["deposit_missing", "withdrawal_processed_missing"].includes(ticket.issue_type)).map((ticket) => ({ case_id: ticket.ticket_id, customer_name: ticket.customer_name, issue_type: ticket.issue_type, priority: ticket.priority, status: "OPEN" }))
        : [];
    const directCapability: "customer_directory" | "payment_failure_cases" | "general_knowledge" | null = customerDirectory ? "customer_directory" : paymentCases ? "payment_failure_cases" : generalKnowledge ? "general_knowledge" : null;
    const requiresAgentRun = !greeting && !directCapability;
    const answer = customerDirectory
      ? `${records.length} synthetic customers are available in the judge snapshot.`
      : paymentCases
        ? `${records.length} synthetic payment-failure cases match the query.`
        : quickReply;
    return {
      signal: {
        conversation_id: id,
        message_type: greeting ? "greeting" : requiresAgentRun ? "support_request" : "direct_capability",
        requires_agent_run: requiresAgentRun,
        is_follow_up: Boolean(conversationId),
        confidence: 0.98,
        response: answer
      },
      customer: customerId ? { customer_id: customerId, synthetic_data_only: true } : null,
      turns: [
        { turn_id: `customer-${Date.now()}`, role: "customer", content: message, created_at: now, delivery_status: "received" },
        ...(answer ? [{ turn_id: `agent-${Date.now()}`, role: "agent" as const, content: answer, created_at: now, delivery_status: "draft" }] : [])
      ],
      capability_route: directCapability ? {
        route_id: `static-${directCapability}`,
        capability: directCapability,
        execution_path: generalKnowledge ? "general_knowledge_llm" : "direct_relational_read",
        requires_agent_run: false,
        confidence: 0.98,
        reason: "Static resilience mode mirrors the verified capability route without a live backend.",
        matched_signals: [directCapability],
        read_only: true,
        data_scope: generalKnowledge ? "public_knowledge" : "synthetic_operational_snapshot",
        event_type: "capability.routed",
        observed_by: "SuperTuriya"
      } : null,
      direct_result: directCapability ? {
        capability: directCapability,
        status: "success",
        answer: answer ?? "Static capability completed.",
        record_count: records.length,
        records,
        aggregates: {},
        source_ids: generalKnowledge ? ["STATIC-DEMO-DISCLOSURE"] : ["STATIC-SYNTHETIC-SNAPSHOT"],
        generated_by: "static_submission_demo",
        fallback_reason: "AMD notebook unavailable after the hackathon session",
        synthetic_data_only: true
      } : null
    };
  }
  return request<ConversationTurnResponse>("/conversations/turn", {
    method: "POST",
    headers: correlationId ? { "X-Correlation-ID": correlationId } : undefined,
    body: JSON.stringify({ message, conversation_id: conversationId, customer_id: customerId })
  });
}

export async function submitSatisfactionFeedback(
  runId: string,
  explicitCsat: number,
  explicitResolution: "yes" | "partially" | "no"
): Promise<Record<string, unknown>> {
  if (STATIC_DEMO) return { recorded: false, mode: "static_submission_demo", message: "Feedback writes require the live API." };
  return request<Record<string, unknown>>("/cx/feedback", {
    method: "POST",
    body: JSON.stringify({ run_id: runId, explicit_csat: explicitCsat, explicit_resolution: explicitResolution })
  });
}

export async function resumeActiveSupportRun(
  onProgress?: (job: RunJobState) => void
): Promise<RunResult | null> {
  if (STATIC_DEMO) return null;
  const jobId = readActiveJob();
  if (!jobId) return null;
  try {
    return await pollRunJob(jobId, onProgress);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      clearActiveJob(jobId);
      return null;
    }
    throw error;
  }
}

async function pollRunJob(jobId: string, onProgress?: (job: RunJobState) => void): Promise<RunResult> {
  let consecutiveTransientFailures = 0;

  for (let attempt = 0; attempt < 180; attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, 2_000));
    let current: RunJobState;
    try {
      current = await request<RunJobState>(`/runs/jobs/${jobId}`);
      consecutiveTransientFailures = 0;
    } catch (error) {
      if (isTransientPollingError(error) && consecutiveTransientFailures < 20) {
        consecutiveTransientFailures += 1;
        console.warn(
          `[Anirvium API] transient polling failure ${consecutiveTransientFailures}/20; the server-side job is still running`,
          error
        );
        continue;
      }
      throw error;
    }
    onProgress?.(current);
    if (current.status === "completed" && current.result) {
      clearActiveJob(jobId);
      return current.result;
    }
    if (current.status === "failed") {
      clearActiveJob(jobId);
      throw new Error(current.error ?? "The AMD agent run failed.");
    }
  }
  throw new Error("The AMD run did not finish within six minutes. Inspect backend and vLLM logs.");
}

function isTransientPollingError(error: unknown): boolean {
  if (error instanceof ApiError) return [429, 502, 503, 504].includes(error.status);
  return error instanceof Error && error.message.includes("Backend unavailable");
}

function persistActiveJob(jobId: string) {
  try {
    window.localStorage.setItem(ACTIVE_JOB_KEY, jobId);
  } catch {
    // The application still works when Safari blocks storage in private mode.
  }
}

function readActiveJob(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_JOB_KEY);
  } catch {
    return null;
  }
}

function clearActiveJob(jobId: string) {
  try {
    if (window.localStorage.getItem(ACTIVE_JOB_KEY) === jobId) {
      window.localStorage.removeItem(ACTIVE_JOB_KEY);
    }
  } catch {
    // Ignore storage failures; polling already completed successfully.
  }
}

export async function fetchWinningDemo(): Promise<WinningDemoResponse> {
  if (STATIC_DEMO) {
    const run = await loadStaticJson<RunResult>("run_CS-002.json");
    return {
      scenario: { title: "CS-002 governed withdrawal recovery", primary_ticket_id: "CS-002", manager_prompt: String(run.metadata.customer_query ?? "Review CS-002"), why_it_wins: ["Shows governed execution and trajectory intelligence"], primary_ticket_summary: "Synthetic third-contact withdrawal complaint" },
      selected_tickets: (await loadStaticJson<SupportTicket[]>("customer_support_tickets.json")).filter((ticket) => ticket.ticket_id === "CS-002"),
      final_actions: run.final_actions,
      visual_evidence_cards: run.visual_evidence_cards,
      customer_response_drafts: run.final_actions.map((item) => ({ ticket_id: item.ticket_id, customer_name: item.customer_name, approval_state: item.approval_state, draft_response: item.draft_response, evidence_ids: item.evidence_ids })),
      primary_ticket_result: run.final_actions[0] ?? null,
      trajectory: run.trajectory,
      graph: run.graph,
      evaluation: run.evaluation,
      failure_diagnosis: run.evaluation.diagnosis,
      optimization_recommendations: run.evaluation.recommendations,
      amd_benchmark_readiness_metadata: { mode: "static_submission_demo", live_amd_evidence: "See amd/benchmark_results_real.md" },
      run
    };
  }
  return request<WinningDemoResponse>("/demo/winning-run");
}

export async function fetchCustomerSupportDemo(): Promise<CustomerSupportDemoResponse> {
  if (STATIC_DEMO) {
    const run = await loadStaticJson<RunResult>("run_CS-002.json");
    return { scenario: { title: "CS-002 governed withdrawal recovery", primary_ticket_id: "CS-002", manager_prompt: String(run.metadata.customer_query ?? "Review CS-002"), why_it_wins: ["Shows Sarvagun execution and SuperTuriya intelligence"] }, selected_tickets: (await loadStaticJson<SupportTicket[]>("customer_support_tickets.json")).filter((ticket) => ticket.ticket_id === "CS-002"), run };
  }
  return request<CustomerSupportDemoResponse>("/demo/customer-support-run");
}

export async function fetchKbLayers(): Promise<KbLayerSummary> {
  if (STATIC_DEMO) return { layer_count: 4, record_count: 34, layers: { policies: { count: 8, domains: ["payments", "verification", "escalation"], high_risk_count: 6 }, procedures: { count: 8, domains: ["support_operations"], high_risk_count: 4 }, templates: { count: 8, domains: ["customer_response"], high_risk_count: 2 }, eval_cases: { count: 10, domains: ["trajectory_evaluation"], high_risk_count: 6 } } };
  return request<KbLayerSummary>("/kb/layers");
}

export async function fetchVectorStatus(): Promise<VectorStatus> {
  if (STATIC_DEMO) return { backend: "static_snapshot", collections: { kb: "anirvium_sarvagun_kb", memory: "anirvium_superturiya_memory", trajectory: "anirvium_superturiya_trajectories" }, dimension: 64, local_index_sizes: { kb: 34, memory: 3, trajectory: 3 }, qdrant_reachable: false };
  return request<VectorStatus>("/kb/vector/status");
}

export async function fetchMemoryStatus(): Promise<MemoryStatus> {
  if (STATIC_DEMO) return { memory_backend: "static_snapshot", redis_configured: false, redis_reachable: false, short_term_sessions: 0, mid_term_sessions: 0, short_term_ttl_seconds: 3600, mid_term_limit: 50 };
  return request<MemoryStatus>("/memory/status");
}

export async function fetchRuntimeReadiness(): Promise<RuntimeReadiness> {
  if (STATIC_DEMO) return { status: "ready", backend_ready: false, model_ready: false, provider: "static_submission_demo", model_id: "precomputed-synthetic-trajectories", available_models: [], runtime: "GitHub Pages resilience mode" };
  return request<RuntimeReadiness>("/health/ready");
}

export async function reindexVectors(): Promise<Record<string, unknown>> {
  if (STATIC_DEMO) return { status: "read_only", mode: "static_submission_demo" };
  return request<Record<string, unknown>>("/kb/vector/reindex", { method: "POST" });
}

export async function searchKb(query: string): Promise<KbSearchResponse> {
  if (STATIC_DEMO) return { query, count: 0, hybrid: true, records: [] };
  return request<KbSearchResponse>(`/kb/search?q=${encodeURIComponent(query)}&hybrid=true`);
}
