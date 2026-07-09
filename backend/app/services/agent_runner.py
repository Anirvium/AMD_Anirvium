from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from app.agents.compliance_agent import ComplianceAgent
from app.agents.critic_agent import CriticEvaluatorAgent
from app.agents.escalation_agent import EscalationAgent
from app.agents.human_escalation_agent import HumanEscalationAgent
from app.agents.learning_extraction_agent import LearningExtractionAgent
from app.agents.optimizer_agent import OptimizerAgent
from app.agents.policy_agent import PolicyCheckerAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.response_agent import ResponseDraftingAgent
from app.agents.retrieval_agent import KnowledgeRetrievalAgent
from app.agents.triage_agent import TriageAgent
from app.agents.visual_evidence_agent import VisualEvidenceAgent
from app.config import get_settings
from app.schemas.evaluation import EvaluationReport
from app.schemas.run import RunRequest, RunResult
from app.schemas.trajectory import TrajectoryResponse, TrajectorySpan
from app.schemas.ticket import SupportTicket
from app.services.data_loader import customers_by_id, evidence_catalog, load_tickets
from app.services.llm_client import build_llm_client
from app.services.memory import add_mid_term_summary, add_short_term_memory, index_trajectory_memory
from app.services.model_router import build_model_router
from app.services.trajectory_logger import TrajectoryLogger


class AgentRunner:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm_client = build_llm_client()
        self.model_router = build_model_router()
        store_dir = Path(__file__).resolve().parent.parent / "data" / "runs"
        self.logger = TrajectoryLogger(store_dir=store_dir, model_name=self.llm_client.model_name)
        self.runs: Dict[str, RunResult] = {}
        self.latest_run_id: str | None = None
        self.winning_demo_run_id: str | None = None

    def run(self, request: RunRequest) -> RunResult:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        selected_tickets = self._select_tickets(request)
        context: Dict[str, Any] = {
            "run_id": run_id,
            "tickets": selected_tickets,
            "dataset": request.dataset,
            "customer_query": request.customer_query,
            "evidence_catalog": evidence_catalog(),
            "customers_by_id": customers_by_id(),
            "llm_client": self.llm_client,
            "model_router": self.model_router,
        }
        spans: List[TrajectorySpan] = []

        agents = [
            VisualEvidenceAgent(self.model_router),
            TriageAgent(),
            KnowledgeRetrievalAgent(),
            PolicyCheckerAgent(),
            EscalationAgent(),
            ResponseDraftingAgent(),
            ComplianceAgent(),
            HumanEscalationAgent(),
        ]

        parent_step_id = None
        for index, agent in enumerate(agents, start=1):
            span = self._run_agent_step(
                run_id=run_id,
                step_index=index,
                parent_step_id=parent_step_id,
                agent_name=agent.name,
                input_summary=self._input_summary(agent.name, selected_tickets, context),
                execute=lambda current_agent=agent: current_agent.run(context),
            )
            spans.append(span)
            parent_step_id = span.step_id

        critic = CriticEvaluatorAgent()
        critic_span = self._run_agent_step(
            run_id=run_id,
            step_index=len(spans) + 1,
            parent_step_id=parent_step_id,
            agent_name=critic.name,
            input_summary="Evaluate the full support-agent trajectory, final actions, evidence coverage, policy compliance, and operational risk.",
            execute=lambda: critic.run(context, spans),
        )
        spans.append(critic_span)
        parent_step_id = critic_span.step_id

        reflection = ReflectionAgent()
        reflection_span = self._run_agent_step(
            run_id=run_id,
            step_index=len(spans) + 1,
            parent_step_id=parent_step_id,
            agent_name=reflection.name,
            input_summary="Review completed support responses, diagnose repeated mistakes, and propose durable behavior improvements.",
            execute=lambda: reflection.run(context),
        )
        spans.append(reflection_span)
        parent_step_id = reflection_span.step_id

        learning = LearningExtractionAgent()
        learning_span = self._run_agent_step(
            run_id=run_id,
            step_index=len(spans) + 1,
            parent_step_id=parent_step_id,
            agent_name=learning.name,
            input_summary="Extract reusable learning artifacts from human handoffs, trajectory logs, transcripts, and satisfaction signals.",
            execute=lambda: learning.run(context),
        )
        spans.append(learning_span)
        parent_step_id = learning_span.step_id

        optimizer = OptimizerAgent()
        optimizer_span = self._run_agent_step(
            run_id=run_id,
            step_index=len(spans) + 1,
            parent_step_id=parent_step_id,
            agent_name=optimizer.name,
            input_summary="Recommend workflow changes from critic findings, deterministic scores, and final support actions.",
            execute=lambda: optimizer.run(context),
        )
        spans.append(optimizer_span)

        graph = self.logger.build_graph(spans)
        evaluation = EvaluationReport(
            run_id=run_id,
            metrics=context["metrics"],
            diagnosis=context["diagnosis"],
            recommendations=context["recommendations"],
            summary=f"Trajectory health score {context['metrics'].overall_score}/100 across {len(selected_tickets)} selected tickets.",
            details={
                "selected_ticket_count": len(selected_tickets),
                "agent_step_count": len(spans),
                "model_name": self.llm_client.model_name,
                "provider": self.settings.llm_provider,
                "compliance_status_counts": self._count_by_key(context.get("final_actions", []), "compliance_status"),
                "human_handoff_count": sum(1 for action in context.get("final_actions", []) if action.get("human_escalation_required")),
                "learning_artifact_count": len(context.get("learning_artifacts", [])),
                "reflection_count": len(context.get("reflections", [])),
            },
        )
        result = RunResult(
            run_id=run_id,
            status="completed",
            selected_ticket_ids=[ticket.ticket_id for ticket in selected_tickets],
            final_actions=context["final_actions"],
            visual_evidence_cards=context.get("visual_evidence_cards", []),
            trajectory=spans,
            graph=graph,
            evaluation=evaluation,
            metadata={
                "created_at": datetime.now(timezone.utc).isoformat(),
                "llm_provider": self.settings.llm_provider,
                "model_name": self.llm_client.model_name,
                "runtime_profile": self.settings.amd_runtime_profile,
                "dataset": request.dataset,
                "customer_query": request.customer_query,
                "model_routes": {
                    "text_agent": self.settings.llm_text_model,
                    "critic_agent": self.settings.llm_critic_model,
                    "embedding": self.settings.llm_embedding_model,
                    "reranker": self.settings.llm_reranker_model,
                },
                "image_video_model_status": "deferred_text_first",
                "memory_backend": self.settings.memory_backend,
                "vector_collections": {
                    "kb": self.settings.vector_kb_collection,
                    "memory": self.settings.vector_memory_collection,
                    "trajectory": self.settings.vector_trajectory_collection,
                },
                "observability": {
                    "trace_schema_version": "anirvium.trajectory.v1",
                    "primary_trace_store": "custom_json_trajectory_logger",
                    "span_count": len(spans),
                    "event_sources": [
                        "agent_span",
                        "tool_action",
                        "evidence_card",
                        "policy_decision",
                        "compliance_decision",
                        "human_handoff",
                        "evaluation_signal",
                        "reflection_signal",
                        "learning_artifact",
                        "optimizer_recommendation",
                    ],
                    "production_export_path": "otel_otlp_optional_after_gpu_validation",
                },
                "synthetic_data_only": True,
            },
        )
        add_short_term_memory(
            run_id,
            f"Run {run_id} completed for {len(selected_tickets)} tickets with score {evaluation.metrics.overall_score}.",
            role="trajectory_logger",
            metadata={"dataset": request.dataset, "selected_ticket_ids": result.selected_ticket_ids},
        )
        add_mid_term_summary(
            run_id,
            evaluation.summary,
            metadata={"dataset": request.dataset, "metric_score": evaluation.metrics.overall_score},
        )
        index_trajectory_memory(result.model_dump(mode="json"))
        self.runs[run_id] = result
        self.latest_run_id = run_id
        self.logger.save_run(run_id, result.model_dump(mode="json"))
        return result

    def get_run(self, run_id: str) -> RunResult | None:
        if run_id in self.runs:
            return self.runs[run_id]
        payload = self.logger.load_run(run_id)
        if payload is None:
            return None
        result = RunResult(**payload)
        self.runs[run_id] = result
        return result

    def get_trajectory(self, run_id: str) -> TrajectoryResponse | None:
        run = self.get_run(run_id)
        if not run:
            return None
        return TrajectoryResponse(run_id=run.run_id, spans=run.trajectory, graph=run.graph)

    def get_latest_run(self) -> RunResult | None:
        if self.latest_run_id is None:
            return None
        return self.get_run(self.latest_run_id)

    def get_or_create_winning_demo(self) -> Dict[str, Any]:
        if self.winning_demo_run_id:
            existing = self.get_run(self.winning_demo_run_id)
            if existing:
                return self._build_winning_demo_payload(existing)

        result = self.run(
            RunRequest(
                selection_mode="selected",
                selected_ticket_ids=["T-001", "T-002", "T-004", "T-008"],
            )
        )
        self.winning_demo_run_id = result.run_id
        return self._build_winning_demo_payload(result)

    def _run_agent_step(
        self,
        *,
        run_id: str,
        step_index: int,
        parent_step_id: str | None,
        agent_name: str,
        input_summary: str,
        execute: Any,
    ) -> TrajectorySpan:
        start = time.perf_counter()
        output = execute()
        latency_ms = int((time.perf_counter() - start) * 1000)
        return self.logger.create_span(
            run_id=run_id,
            step_index=step_index,
            parent_step_id=parent_step_id,
            agent_name=agent_name,
            input_summary=input_summary,
            full_output=output,
            latency_ms=latency_ms,
        )

    def _select_tickets(self, request: RunRequest) -> List[SupportTicket]:
        tickets = load_tickets(request.dataset)
        if request.selection_mode == "all":
            return tickets
        if request.selection_mode == "selected":
            selected_ids = set(request.selected_ticket_ids or [])
            return [ticket for ticket in tickets if ticket.ticket_id in selected_ids]
        return [ticket for ticket in tickets if ticket.priority in {"high", "critical"}]

    def _input_summary(self, agent_name: str, tickets: List[SupportTicket], context: Dict[str, Any]) -> str:
        ids = ", ".join(ticket.ticket_id for ticket in tickets)
        if agent_name == "Knowledge Retrieval Agent":
            return f"Retrieve KB and policy evidence for selected tickets: {ids}."
        if agent_name == "Attachment Evidence Agent":
            return f"Extract lightweight attachment evidence cards without an image/video model for tickets: {ids}."
        if agent_name == "Policy Checker Agent":
            return f"Apply approval and policy gates using retrieved evidence for tickets: {ids}."
        if agent_name == "Escalation Agent":
            return f"Route selected tickets to the right owner, urgency, and next action: {ids}."
        if agent_name == "Response Drafting Agent":
            return f"Draft customer-safe replies using policy constraints and escalation outputs for tickets: {ids}."
        if agent_name == "Compliance Agent":
            return f"Check drafted replies against legal, regulatory, company, privacy, and evidence rules for tickets: {ids}."
        if agent_name == "Human Escalation Agent":
            return f"Route low-confidence, blocked, or approval-required support cases to human review for tickets: {ids}."
        if agent_name == "Reflection Agent":
            return f"Reflect on completed support responses and repeated failure patterns for tickets: {ids}."
        if agent_name == "Learning Extraction Agent":
            return f"Extract learning artifacts from handoffs, trajectory logs, transcripts, and satisfaction signals for tickets: {ids}."
        return f"Classify selected support tickets: {ids}."

    def _count_by_key(self, rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            value = str(row.get(key, "UNKNOWN"))
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _build_winning_demo_payload(self, result: RunResult) -> Dict[str, Any]:
        tickets_by_id = {ticket.ticket_id: ticket for ticket in load_tickets()}
        selected_tickets = [tickets_by_id[ticket_id] for ticket_id in result.selected_ticket_ids if ticket_id in tickets_by_id]
        t001_action = next((action for action in result.final_actions if action.ticket_id == "T-001"), None)
        return {
            "scenario": {
                "title": "Enterprise SLA outage trajectory intelligence demo",
                "primary_ticket_id": "T-001",
                "manager_prompt": (
                    "Analyze today's high-priority customer support queue. Identify SLA risks, "
                    "policy-sensitive cases, escalation needs, and draft safe customer responses. "
                    "Then evaluate the agent trajectory and recommend how the support agent can improve."
                ),
                "why_it_wins": [
                    "Shows enterprise SLA risk before breach.",
                    "Connects every action to KB and policy evidence IDs.",
                    "Keeps sensitive actions in approval-aware draft state.",
                    "Diagnoses concrete workflow flaws and recommends testable fixes.",
                    "Displays AMD vLLM/ROCm benchmark readiness without fake claims.",
                ],
                "primary_ticket_summary": (
                    "T-001 is an enterprise production outage for ACME Corp with angry sentiment, "
                    "churn risk, and an SLA deadline inside 60 minutes."
                ),
            },
            "selected_tickets": [ticket.model_dump() for ticket in selected_tickets],
            "final_actions": [action.model_dump() for action in result.final_actions],
            "visual_evidence_cards": [card.model_dump() for card in result.visual_evidence_cards],
            "customer_response_drafts": [
                {
                    "ticket_id": action.ticket_id,
                    "customer_name": action.customer_name,
                    "approval_state": action.approval_state,
                    "draft_response": action.draft_response,
                    "evidence_ids": action.evidence_ids,
                }
                for action in result.final_actions
            ],
            "primary_ticket_result": t001_action.model_dump() if t001_action else None,
            "trajectory": [span.model_dump(mode="json") for span in result.trajectory],
            "graph": result.graph.model_dump(),
            "evaluation": result.evaluation.model_dump(),
            "failure_diagnosis": [item.model_dump() for item in result.evaluation.diagnosis],
            "optimization_recommendations": [item.model_dump() for item in result.evaluation.recommendations],
            "amd_benchmark_readiness_metadata": {
                "status": "AMD execution pending",
                "real_evidence_available": False,
                "claim_boundary": (
                    "Real AMD benchmark pending. Scripts and runbook are prepared. "
                    "Sample files are marked as sample and are not claimed as verified AMD execution."
                ),
                "future_real_evidence_paths": [
                    "amd/logs/benchmark_amd_real_<date>.json",
                    "amd/benchmark_results_real.md",
                    "amd/screenshots/vllm_running.png",
                    "amd/screenshots/benchmark_output.png",
                    "amd/screenshots/dashboard_amd_panel.png",
                ],
                "runbook": "amd/README_AMD_USAGE.md",
                "runtime_strategy": "Use text inference first. Critic can be validated after text. Image/video model loading is deferred.",
            },
            "run": result.model_dump(mode="json"),
        }

    def get_or_create_customer_support_demo(self) -> Dict[str, Any]:
        result = self.run(RunRequest(selection_mode="all_high_priority", dataset="customer_support"))
        tickets_by_id = {ticket.ticket_id: ticket for ticket in load_tickets("customer_support")}
        selected_tickets = [tickets_by_id[ticket_id] for ticket_id in result.selected_ticket_ids if ticket_id in tickets_by_id]
        return {
            "scenario": {
                "title": "Policy-safe multimodal customer support trajectory demo",
                "primary_ticket_id": "CS-002",
                "manager_prompt": (
                    "Analyze the high-risk customer support queue for payment, verification, bonus, "
                    "and account-access issues. Retrieve policy evidence, apply approval gates, draft safe responses, "
                    "evaluate the trajectory, and recommend workflow improvements."
                ),
                "why_it_wins": [
                    "Uses anonymized real support-domain knowledge instead of generic SaaS examples.",
                    "Grounds payment, verification, bonus, and account-access replies in curated KB layers.",
                    "Keeps high-risk actions behind approval and evidence gates.",
                    "Shows a direct path from source documents to policies, procedures, templates, and eval cases.",
                ],
            },
            "selected_tickets": [ticket.model_dump() for ticket in selected_tickets],
            "run": result.model_dump(mode="json"),
        }
