import type {
  CustomerSupportDemoResponse,
  KbLayerSummary,
  KbSearchResponse,
  MemoryStatus,
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
    throw new Error(`${response.status} ${response.statusText}`);
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

  const job = await request<{ job_id: string; status: string }>("/runs/async", {
    method: "POST",
    body: JSON.stringify(body)
  });

  for (let attempt = 0; attempt < 180; attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, 2_000));
    const current = await request<{ status: string; result: RunResult | null; error: string | null }>(`/runs/jobs/${job.job_id}`);
    if (current.status === "completed" && current.result) return current.result;
    if (current.status === "failed") throw new Error(current.error ?? "The AMD agent run failed.");
  }
  throw new Error("The AMD run did not finish within six minutes. Inspect backend and vLLM logs.");
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

export async function reindexVectors(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/kb/vector/reindex", { method: "POST" });
}

export async function searchKb(query: string): Promise<KbSearchResponse> {
  return request<KbSearchResponse>(`/kb/search?q=${encodeURIComponent(query)}&hybrid=true`);
}
