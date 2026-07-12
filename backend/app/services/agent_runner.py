from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List
from uuid import uuid4

from app.agents.compliance_agent import ComplianceAgent
from app.agents.critic_agent import CriticEvaluatorAgent
from app.agents.escalation_agent import EscalationAgent
from app.agents.human_escalation_agent import HumanEscalationAgent
from app.agents.learning_extraction_agent import LearningExtractionAgent
from app.agents.optimizer_agent import OptimizerAgent
from app.agents.planner_agent import PlannerAgent
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
from app.services.intent_router import resolve_customer_support_intent
from app.services.memory import add_mid_term_summary, add_short_term_memory, index_trajectory_memory, search_long_term_memory
from app.services.model_router import build_model_router
from app.services.observability import bind_observability_context
from app.services.relational_store import get_relational_repository
from app.services.sarvagun_lifecycle import sarvagun_lifecycle
from app.services.trajectory_logger import TrajectoryLogger


class InvalidRunSelectionError(ValueError):
    """Raised when a request cannot resolve to any runnable support case."""


logger = logging.getLogger("uvicorn.error")


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
        self.customer_support_demo_run_id: str | None = None
        self._customer_support_demo_lock = Lock()
        self._hydrate_recent_trajectory_memory()

    def run(
        self,
        request: RunRequest,
        progress_callback: Callable[[int, int, str, str], None] | None = None,
    ) -> RunResult:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        bind_observability_context(correlation_id=request.correlation_id, run_id=run_id)
        selected_tickets = self._select_tickets(request)
        if not selected_tickets:
            raise InvalidRunSelectionError("No valid support tickets matched the requested selection")
        if request.customer_id and any(ticket.customer_id != request.customer_id for ticket in selected_tickets):
            raise InvalidRunSelectionError(
                "The requested customer_id does not match the selected support case"
            )
        intent = resolve_customer_support_intent(request.customer_query) if request.dataset == "customer_support" else None
        memory_query = request.customer_query or " ".join(ticket.message for ticket in selected_tickets)
        prior_memories = search_long_term_memory(memory_query, limit=3, trusted_only=True) if memory_query else []
        compact_prior_memories = self._compact_prior_memories(prior_memories)
        context: Dict[str, Any] = {
            "run_id": run_id,
            "tickets": selected_tickets,
            "dataset": request.dataset,
            "customer_query": request.customer_query,
            "correlation_id": request.correlation_id,
            "evidence_catalog": evidence_catalog(),
            "customers_by_id": customers_by_id(),
            "llm_client": self.llm_client,
            "model_router": self.model_router,
            "enable_auxiliary_llm_reviews": self.settings.llm_auxiliary_reviews,
            "resolved_intent": intent.issue_type if intent else None,
            "prior_trajectory_memory": compact_prior_memories,
        }
        if request.dataset == "customer_support":
            context.update(
                sarvagun_lifecycle.prepare(
                    run_id=run_id,
                    request=request,
                    tickets=selected_tickets,
                    prior_memories=compact_prior_memories,
                )
            )
        spans: List[TrajectorySpan] = []

        agents = [
            PlannerAgent(),
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
                execute=lambda current_agent=agent: self._execute_agent(current_agent, context),
                correlation_id=request.correlation_id,
                progress_callback=progress_callback,
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
            correlation_id=request.correlation_id,
            progress_callback=progress_callback,
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
            correlation_id=request.correlation_id,
            progress_callback=progress_callback,
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
            correlation_id=request.correlation_id,
            progress_callback=progress_callback,
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
            correlation_id=request.correlation_id,
            progress_callback=progress_callback,
        )
        spans.append(optimizer_span)

        sarvagun = None
        superturiya = None
        if request.dataset == "customer_support":
            sarvagun, superturiya = sarvagun_lifecycle.finalize(context=context, spans=spans, request=request)

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
                "sarvagun_execution_mode": request.execution_mode,
                "superturiya_event_count": superturiya.event_count if superturiya else 0,
                "cx_quality_rubric": sarvagun.satisfaction.rubric if sarvagun else {},
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
            sarvagun=sarvagun,
            superturiya=superturiya,
            metadata={
                "created_at": datetime.now(timezone.utc).isoformat(),
                "llm_provider": self.settings.llm_provider,
                "model_name": self.llm_client.model_name,
                "runtime_profile": self.settings.amd_runtime_profile,
                "dataset": request.dataset,
                "customer_query": request.customer_query,
                "correlation_id": request.correlation_id,
                "system_identity": {
                    "platform": "Anirvium AI",
                    "execution_system": "Sarvagun",
                    "intelligence_system": "SuperTuriya",
                },
                "execution_mode": request.execution_mode,
                "conversation_id": sarvagun.conversation.conversation_id if sarvagun else request.conversation_id,
                "query_resolution": {
                    "requested_ticket_ids": request.selected_ticket_ids or [],
                    "resolved_ticket_ids": [ticket.ticket_id for ticket in selected_tickets],
                    "resolved_issue_type": intent.issue_type if intent else None,
                    "confidence": intent.confidence if intent else None,
                    "query_routed": self._query_was_routed(request, intent),
                    "customer_identity_preserved": self._customer_identity_preserved(request, selected_tickets),
                    "routing_strategy": (
                        "issue_profile_overlay_on_selected_customer_case"
                        if self._query_was_routed(request, intent)
                        else "selected_case_or_priority_selection"
                    ),
                },
                "model_routes": {
                    "sarvagun_text": {
                        "active_model": self.llm_client.model_name,
                        "provider": self.settings.llm_provider,
                        "active": self.settings.llm_provider.lower() in {"openai", "openai_compatible", "llm"},
                    },
                    "superturiya_critic": {
                        "active_model": self.llm_client.model_name if self.settings.llm_auxiliary_reviews else "deterministic-trajectory-evaluator-v1",
                        "configured_optional_model": self.settings.llm_critic_model,
                        "llm_review_active": self.settings.llm_auxiliary_reviews,
                    },
                    "embedding": {
                        "active_model": "deterministic-token-hash-64d",
                        "configured_optional_model": self.settings.llm_embedding_model,
                        "external_model_active": False,
                    },
                    "reranker": {
                        "active_model": "deterministic-hybrid-rank-fusion",
                        "configured_optional_model": self.settings.llm_reranker_model,
                        "external_model_active": False,
                    },
                    "classification_and_guardrails": {
                        "active_model": "deterministic-rules",
                        "external_model_active": False,
                    },
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
                        "planner_contract",
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
                        "trajectory_property_graph",
                        "sarvagun_conversation_event",
                        "enterprise_tool_execution",
                        "superturiya_intelligence_event",
                    ],
                    "production_export_path": "otel_otlp_optional_after_gpu_validation",
                },
                "synthetic_data_only": True,
                "learning_loop": {
                    "mode": "retrieve_evaluate_recommend_reuse",
                    "prior_memories_recalled": len(context.get("prior_trajectory_memory", [])),
                    "recalled_memory_ids": [item["id"] for item in context.get("prior_trajectory_memory", [])],
                    "applied_learning_ids": superturiya.applied_memory_ids if superturiya else [],
                    "reuse_stage": "pre_plan_strategy_and_response_drafting",
                    "writes_trajectory_memory": True,
                    "automatic_policy_mutation": False,
                },
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
        if sarvagun and superturiya:
            sarvagun_lifecycle.persist(run_id=run_id, sarvagun=sarvagun, superturiya=superturiya)
        try:
            result.metadata["relational_persistence"] = get_relational_repository().persist_run_result(result)
        except Exception as exc:
            # The JSON trajectory remains the reliable demo fallback. Surface
            # relational degradation explicitly instead of failing the run or
            # claiming that the write succeeded.
            result.metadata["relational_persistence"] = {
                "backend": "sqlite",
                "persisted": False,
                "error": type(exc).__name__,
            }
        self.runs[run_id] = result
        self.latest_run_id = run_id
        self.logger.save_run(run_id, result.model_dump(mode="json"))
        return result

    def _execute_agent(self, agent: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        output = agent.run(context)
        if context.get("dataset") == "customer_support":
            return sarvagun_lifecycle.after_agent(agent.name, context, output)
        return output

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
        correlation_id: str | None = None,
        progress_callback: Callable[[int, int, str, str], None] | None = None,
    ) -> TrajectorySpan:
        total_steps = 13
        if progress_callback:
            progress_callback(step_index, total_steps, agent_name, "running")
        logger.info(
            "agent_step_started correlation_id=%s run_id=%s step=%s agent=%s",
            correlation_id,
            run_id,
            step_index,
            agent_name,
        )
        start = time.perf_counter()
        try:
            output = execute()
        except Exception:
            logger.exception(
                "agent_step_failed correlation_id=%s run_id=%s step=%s agent=%s",
                correlation_id,
                run_id,
                step_index,
                agent_name,
            )
            raise
        latency_ms = int((time.perf_counter() - start) * 1000)
        span = self.logger.create_span(
            run_id=run_id,
            step_index=step_index,
            parent_step_id=parent_step_id,
            agent_name=agent_name,
            input_summary=input_summary,
            full_output=output,
            latency_ms=latency_ms,
        )
        if progress_callback:
            progress_callback(step_index, total_steps, agent_name, "completed")
        logger.info(
            "agent_step_completed correlation_id=%s run_id=%s step=%s agent=%s duration_ms=%s tokens_in=%s tokens_out=%s risks=%s",
            correlation_id,
            run_id,
            step_index,
            agent_name,
            latency_ms,
            span.tokens_in,
            span.tokens_out,
            len(span.risk_flags),
        )
        return span

    def _select_tickets(self, request: RunRequest) -> List[SupportTicket]:
        tickets = load_tickets(request.dataset)
        if request.selection_mode == "all":
            return tickets
        if request.selection_mode == "selected":
            selected_ids = set(request.selected_ticket_ids or [])
            selected = [ticket for ticket in tickets if ticket.ticket_id in selected_ids]
            if request.dataset == "customer_support" and request.customer_query:
                intent = resolve_customer_support_intent(request.customer_query)
                if intent:
                    matching_selected = [ticket for ticket in selected if ticket.issue_type == intent.issue_type]
                    if matching_selected:
                        return matching_selected[:1]
                    canonical = next((ticket for ticket in tickets if ticket.issue_type == intent.issue_type), None)
                    if canonical:
                        if selected:
                            selected_customer_case = selected[0]
                            return [
                                selected_customer_case.model_copy(
                                    update={
                                        "issue_type": canonical.issue_type,
                                        "priority": canonical.priority,
                                        "message": request.customer_query,
                                        "previous_interactions": [],
                                        "attachments": [],
                                        "expected_evidence_ids": list(canonical.expected_evidence_ids),
                                    }
                                )
                            ]
                        return [canonical]
            return selected
        return [ticket for ticket in tickets if ticket.priority in {"high", "critical"}]

    def _query_was_routed(self, request: RunRequest, intent: Any) -> bool:
        if intent is None or request.dataset != "customer_support":
            return False
        requested_ids = set(request.selected_ticket_ids or [])
        requested_tickets = [
            ticket for ticket in load_tickets(request.dataset) if ticket.ticket_id in requested_ids
        ]
        return bool(requested_tickets and all(ticket.issue_type != intent.issue_type for ticket in requested_tickets))

    def _customer_identity_preserved(
        self,
        request: RunRequest,
        selected_tickets: List[SupportTicket],
    ) -> bool:
        if not request.selected_ticket_ids:
            return True
        requested_ids = set(request.selected_ticket_ids)
        requested_customer_ids = {
            ticket.customer_id
            for ticket in load_tickets(request.dataset)
            if ticket.ticket_id in requested_ids
        }
        return {ticket.customer_id for ticket in selected_tickets}.issubset(requested_customer_ids)

    def _compact_prior_memories(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []
        for record in records:
            memory_type = record.get("memory_type") or record.get("metadata", {}).get("memory_type")
            trust_scope = record.get("trust_scope") or record.get("metadata", {}).get("trust_scope")
            if memory_type not in {"trajectory_summary", "sarvagun_transcript"} or trust_scope != "superturiya_evaluated_memory":
                continue
            compact.append(
                {
                    "id": record.get("id"),
                    "run_id": record.get("metadata", {}).get("run_id") or record.get("run_id"),
                    "text": str(record.get("text", ""))[:1800],
                    "relevance": record.get("vector_score"),
                    "memory_type": memory_type,
                    "trust_scope": trust_scope,
                }
            )
        return compact

    def _hydrate_recent_trajectory_memory(self) -> None:
        if self.settings.llm_provider == "mock":
            return
        candidates = sorted(
            self.logger.store_dir.glob("run_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        hydrated = 0
        for path in candidates:
            payload = self.logger.load_run(path.stem)
            if not payload:
                continue
            metadata = payload.get("metadata", {})
            if metadata.get("dataset") != "customer_support":
                continue
            if metadata.get("llm_provider") != self.settings.llm_provider:
                continue
            try:
                index_trajectory_memory(payload)
            except Exception:
                continue
            hydrated += 1
            if hydrated >= 12:
                break

    def _input_summary(self, agent_name: str, tickets: List[SupportTicket], context: Dict[str, Any]) -> str:
        ids = ", ".join(ticket.ticket_id for ticket in tickets)
        if agent_name == "Planner Agent":
            return f"Build a plan-driven support workflow, stop conditions, and evidence contract for tickets: {ids}."
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
        with self._customer_support_demo_lock:
            result = self._get_cached_customer_support_demo_run()
            if result is None:
                result = self.run(RunRequest(selection_mode="all_high_priority", dataset="customer_support"))
                result.metadata["demo_kind"] = "customer_support_curated"
                self.logger.save_run(result.run_id, result.model_dump(mode="json"))
                self.customer_support_demo_run_id = result.run_id

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

    def _get_cached_customer_support_demo_run(self) -> RunResult | None:
        if self.customer_support_demo_run_id:
            existing = self.get_run(self.customer_support_demo_run_id)
            if existing:
                return existing

        expected_ticket_ids = {
            ticket.ticket_id
            for ticket in load_tickets("customer_support")
            if ticket.priority in {"high", "critical"}
        }
        candidates = sorted(
            self.logger.store_dir.glob("run_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in candidates:
            payload = self.logger.load_run(path.stem)
            if not payload:
                continue
            metadata = payload.get("metadata", {})
            if metadata.get("dataset") != "customer_support":
                continue
            if metadata.get("llm_provider") != self.settings.llm_provider:
                continue
            if metadata.get("customer_query") is not None:
                continue
            try:
                result = RunResult(**payload)
            except (TypeError, ValueError):
                continue
            if result.status != "completed" or len(result.trajectory) != 13:
                continue
            if set(result.selected_ticket_ids) != expected_ticket_ids:
                continue
            self.runs[result.run_id] = result
            self.latest_run_id = result.run_id
            self.customer_support_demo_run_id = result.run_id
            return result
        return None
