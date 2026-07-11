import type {
  CustomerSupportDemoResponse,
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
    { requestId: response.headers.get("x-request-id") }
  );

  return response.json() as Promise<T>;
}

export async function fetchTickets(): Promise<SupportTicket[]> {
  const payload = await request<{ tickets: SupportTicket[] }>("/tickets");
  return payload.tickets;
}

export async function fetchCustomerSupportTickets(): Promise<SupportTicket[]> {
  const payload = await request<{ tickets: SupportTicket[] }>("/tickets?dataset=customer_support");
  return payload.tickets;
}

export async function runSupportAgent(selectedTicketIds?: string[], customerQuery?: string): Promise<RunResult> {
  const body = selectedTicketIds?.length
    ? { selection_mode: "selected", selected_ticket_ids: selectedTicketIds, dataset: "customer_support", customer_query: customerQuery }
    : { selection_mode: "all_high_priority", dataset: "customer_support" };

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
  onProgress: (job: RunJobState) => void
): Promise<RunResult> {
  const body = selectedTicketIds?.length
    ? { selection_mode: "selected", selected_ticket_ids: selectedTicketIds, dataset: "customer_support", customer_query: customerQuery }
    : { selection_mode: "all_high_priority", dataset: "customer_support", customer_query: customerQuery };

  const job = await request<RunJobState>("/runs/async", {
    method: "POST",
    body: JSON.stringify(body)
  });

  persistActiveJob(job.job_id);
  onProgress(job);
  return pollRunJob(job.job_id, onProgress);
}

export async function resumeActiveSupportRun(
  onProgress?: (job: RunJobState) => void
): Promise<RunResult | null> {
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
  return request<WinningDemoResponse>("/demo/winning-run");
}

export async function fetchCustomerSupportDemo(): Promise<CustomerSupportDemoResponse> {
  return request<CustomerSupportDemoResponse>("/demo/customer-support-run");
}

export async function fetchKbLayers(): Promise<KbLayerSummary> {
  return request<KbLayerSummary>("/kb/layers");
}

export async function fetchVectorStatus(): Promise<VectorStatus> {
  return request<VectorStatus>("/kb/vector/status");
}

export async function fetchMemoryStatus(): Promise<MemoryStatus> {
  return request<MemoryStatus>("/memory/status");
}

export async function fetchRuntimeReadiness(): Promise<RuntimeReadiness> {
  return request<RuntimeReadiness>("/health/ready");
}

export async function reindexVectors(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/kb/vector/reindex", { method: "POST" });
}

export async function searchKb(query: string): Promise<KbSearchResponse> {
  return request<KbSearchResponse>(`/kb/search?q=${encodeURIComponent(query)}&hybrid=true`);
}
