export type TicketPriority = "low" | "medium" | "high" | "critical";

export interface SupportTicket {
  ticket_id: string;
  customer_id: string;
  customer_name: string;
  plan: "free" | "pro" | "business" | "enterprise";
  issue_type: string;
  priority: TicketPriority;
  message: string;
  created_at: string;
  sla_deadline: string;
  sentiment: string;
  previous_interactions: string[];
  attachments: Array<Record<string, unknown>>;
  expected_evidence_ids: string[];
}

export interface FinalAction {
  ticket_id: string;
  customer_name: string;
  recommended_escalation: string;
  owner: string;
  urgency: string;
  approval_state: string;
  draft_response: string;
  evidence_ids: string[];
  risk_flags: string[];
  next_action: string;
  confidence_score?: number;
  compliance_status?: string;
  human_escalation_required?: boolean;
  handoff_team?: string | null;
  handoff_reason?: string | null;
  handoff_summary?: string | null;
}

export interface VisualEvidenceCard {
  evidence_id: string;
  ticket_id: string;
  source_type: "image" | "video" | "screenshot" | "document" | "text_attachment" | "structured_log" | "unknown";
  filename: string;
  summary: string;
  ocr_text: string;
  visual_findings: string[];
  timestamp_refs: string[];
  supported_claims: string[];
  risk_flags: string[];
  confidence: number;
  requires_policy_check: boolean;
  model_name: string;
  raw_modality?: string | null;
}

export interface TrajectorySpan {
  run_id: string;
  step_id: string;
  parent_step_id: string | null;
  agent_name: string;
  input_summary: string;
  output_summary: string;
  full_output: Record<string, unknown>;
  tools_used: string[];
  evidence_ids: string[];
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  model_name: string;
  confidence: number;
  risk_flags: string[];
  approval_state: string;
  timestamp: string;
}

export interface TrajectoryGraphNode {
  id: string;
  label: string;
  status: string;
  score: number;
  risk_flags: string[];
}

export interface TrajectoryGraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface EvaluationMetrics {
  task_completion: number;
  evidence_grounding: number;
  policy_compliance: number;
  hallucination_risk: number;
  escalation_quality: number;
  actionability: number;
  missing_information: number;
  customer_tone: number;
  token_efficiency: number;
  latency_efficiency: number;
  overall_score: number;
}

export interface DiagnosisItem {
  category: string;
  severity: string;
  ticket_id?: string | null;
  message: string;
  evidence_ids: string[];
  suggested_fix: string;
  failure_type: string;
  affected_agent: string;
  business_impact: string;
  recommended_fix: string;
  metric_impact: string[];
  confidence: number;
}

export interface OptimizationRecommendation {
  recommendation_id: string;
  title: string;
  change_type: string;
  rationale: string;
  expected_impact: string;
  before: string;
  after: string;
  related_ticket_ids: string[];
  priority: string;
  target_agent: string;
  problem: string;
  root_cause: string;
  fix: string;
  expected_metric_lift: Record<string, string>;
  implementation_hint: string;
}

export interface EvaluationReport {
  run_id: string;
  metrics: EvaluationMetrics;
  diagnosis: DiagnosisItem[];
  recommendations: OptimizationRecommendation[];
  summary: string;
  details: Record<string, unknown>;
}

export interface RunResult {
  run_id: string;
  status: string;
  selected_ticket_ids: string[];
  final_actions: FinalAction[];
  visual_evidence_cards: VisualEvidenceCard[];
  trajectory: TrajectorySpan[];
  graph: {
    nodes: TrajectoryGraphNode[];
    edges: TrajectoryGraphEdge[];
  };
  evaluation: EvaluationReport;
  metadata: Record<string, unknown>;
}

export interface AmdBenchmark {
  provider: string;
  backend: string;
  gpu: string;
  model: string;
  runtime_profile?: string;
  selected_model_stack?: Record<string, string>;
  mode: string;
  status?: string;
  real_evidence_available?: boolean;
  tokens_per_second: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  batch_evaluation_throughput: string;
  average_trajectory_score: number;
  benchmark_log_path: string;
  future_real_evidence_paths?: string[];
  notes: string[];
}

export interface WinningDemoResponse {
  scenario: {
    title: string;
    primary_ticket_id: string;
    manager_prompt: string;
    why_it_wins: string[];
    primary_ticket_summary: string;
  };
  selected_tickets: SupportTicket[];
  final_actions: FinalAction[];
  visual_evidence_cards: VisualEvidenceCard[];
  customer_response_drafts: Array<{
    ticket_id: string;
    customer_name: string;
    approval_state: string;
    draft_response: string;
    evidence_ids: string[];
  }>;
  primary_ticket_result: FinalAction | null;
  trajectory: TrajectorySpan[];
  graph: RunResult["graph"];
  evaluation: EvaluationReport;
  failure_diagnosis: DiagnosisItem[];
  optimization_recommendations: OptimizationRecommendation[];
  amd_benchmark_readiness_metadata: Record<string, unknown>;
  run: RunResult;
}

export interface CustomerSupportDemoResponse {
  scenario: {
    title: string;
    primary_ticket_id: string;
    manager_prompt: string;
    why_it_wins: string[];
  };
  selected_tickets: SupportTicket[];
  run: RunResult;
}

export interface KbLayerSummary {
  layer_count: number;
  record_count: number;
  layers: Record<string, {
    count: number;
    domains: string[];
    high_risk_count: number;
  }>;
}

export interface VectorStatus {
  backend: string;
  collections: Record<string, string>;
  dimension: number;
  local_index_sizes: Record<string, number>;
  qdrant_reachable: boolean;
  points_count?: number;
}

export interface MemoryStatus {
  memory_backend: string;
  redis_configured: boolean;
  redis_reachable: boolean;
  short_term_sessions: number;
  mid_term_sessions: number;
  short_term_ttl_seconds: number;
  mid_term_limit: number;
}

export interface KbSearchRecord {
  id: string;
  title: string;
  layer?: string;
  domain?: string;
  risk_level?: string;
  retrieval_source?: string;
  hybrid_score?: number;
}

export interface KbSearchResponse {
  query: string;
  count: number;
  hybrid: boolean;
  records: KbSearchRecord[];
}
