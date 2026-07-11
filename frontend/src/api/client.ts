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
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {})
      },
      ...options
    });
  } catch {
    throw new Error("Backend unavailable. Start the API on port 8000, then reload the demo.");
  }

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

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

  return request<RunResult>("/runs", {
    method: "POST",
    body: JSON.stringify(body)
  });
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
