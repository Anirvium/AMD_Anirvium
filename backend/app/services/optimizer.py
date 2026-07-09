from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from app.schemas.evaluation import DiagnosisItem, EvaluationMetrics, OptimizationRecommendation


class OptimizationEngine:
    def recommend(
        self,
        diagnosis: Iterable[DiagnosisItem],
        metrics: EvaluationMetrics,
    ) -> List[OptimizationRecommendation]:
        items = list(diagnosis)
        categories = Counter(item.category for item in items)
        recommendations: List[OptimizationRecommendation] = []

        if categories.get("missing_evidence") or metrics.evidence_grounding < 0.95:
            tickets = sorted({item.ticket_id for item in items if item.category == "missing_evidence" and item.ticket_id})
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id="OPT-001",
                    title="Add mandatory evidence checklist",
                    change_type="mandatory_check",
                    rationale="Every material recommendation should be backed by KB or policy IDs before the response drafter runs.",
                    expected_impact="+8 to +12 evidence grounding points",
                    before="The drafter accepts whatever retrieval returns.",
                    after="The drafter must confirm each selected ticket has expected KB and policy evidence IDs.",
                    related_ticket_ids=tickets,
                    priority="HIGH",
                    target_agent="Knowledge Retrieval Agent",
                    problem="A final recommendation can be drafted without all expected KB and policy evidence IDs.",
                    root_cause="The retrieval handoff is treated as advisory rather than a required evidence contract.",
                    fix="Require an evidence checklist keyed by ticket_id before response drafting can proceed.",
                    expected_metric_lift={"evidence_grounding": "+0.08", "hallucination_risk": "-0.05"},
                    implementation_hint="Validate ticket.expected_evidence_ids against final_action.evidence_ids before Response Drafting Agent emits a draft.",
                )
            )

        if categories.get("weak_response") or metrics.missing_information > 0.2:
            tickets = sorted({item.ticket_id for item in items if item.category == "weak_response" and item.ticket_id})
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id="OPT-002",
                    title="Require owner and update cadence for urgent cases",
                    change_type="mandatory_check",
                    rationale="Critical support replies need an assigned owner and clear update cadence to reduce escalation ambiguity.",
                    expected_impact="+6 actionability points and lower SLA risk",
                    before="High-urgency drafts can omit next-update timing.",
                    after="Critical and high-priority drafts include owner, route, urgency, and next-update timing.",
                    related_ticket_ids=tickets,
                    priority="HIGH",
                    target_agent="Escalation Agent",
                    problem="High-risk tickets can have an escalation route but no customer-visible update cadence.",
                    root_cause="The escalation schema has owner and next_action but the response drafting rule does not require next_update timing.",
                    fix="Add mandatory next_update_at or update_cadence fields for critical and high-priority tickets.",
                    expected_metric_lift={"actionability": "+0.12", "missing_information": "-0.20"},
                    implementation_hint="Update response_agent.py templates and evaluator.py missing_information rule to require next update language.",
                )
            )

        if categories.get("policy_violation") or categories.get("unsafe_action_without_approval") or metrics.policy_compliance < 1:
            tickets = sorted(
                {
                    item.ticket_id
                    for item in items
                    if item.category in {"policy_violation", "unsafe_action_without_approval"} and item.ticket_id
                }
            )
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id="OPT-003",
                    title="Insert sensitive-action approval gate",
                    change_type="tool_routing",
                    rationale="Refund, security, deletion, and compensation workflows must stop at draft recommendation until approved.",
                    expected_impact="Blocks critical policy failures before customer send",
                    before="The policy checker and drafter run as adjacent steps.",
                    after="Policy checker emits APPROVAL_REQUIRED and routes sensitive outputs to human review.",
                    related_ticket_ids=tickets,
                    priority="CRITICAL",
                    target_agent="Policy Checker Agent",
                    problem="Sensitive support actions can become customer-facing commitments if approval state is not enforced.",
                    root_cause="Approval state is generated but needs to be treated as a hard workflow gate.",
                    fix="Block final-send state for refund, security, deletion, compensation, legal, and enterprise SLA actions unless approved.",
                    expected_metric_lift={"policy_compliance": "+0.18", "hallucination_risk": "-0.08"},
                    implementation_hint="Add approval_state checks before any customer-send integration and keep responses as DRAFT_RECOMMENDATION or APPROVAL_REQUIRED.",
                )
            )

        if categories.get("excessive_token_usage") or metrics.token_efficiency < 0.85:
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id="OPT-004",
                    title="Compress retrieval handoff",
                    change_type="token_reduction",
                    rationale="Later agents need evidence IDs and short summaries, not full KB and policy bodies.",
                    expected_impact="15-30 percent lower token usage on batch queue analysis",
                    before="Full evidence text can be repeated in multiple spans.",
                    after="Retrieval emits normalized evidence cards and one-line policy constraints.",
                    priority="MEDIUM",
                    target_agent="Knowledge Retrieval Agent",
                    problem="Batch analysis can spend tokens repeating full evidence text across downstream agent steps.",
                    root_cause="Evidence cards are not aggressively compressed before handoff.",
                    fix="Emit compact evidence cards with id, title, one-line summary, and constraint only.",
                    expected_metric_lift={"token_efficiency": "+0.15", "latency_efficiency": "+0.08"},
                    implementation_hint="Keep KB body text in the catalog and pass only compact evidence_cards through the trajectory context.",
                )
            )

        if not recommendations:
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id="OPT-000",
                    title="Keep current workflow and collect human approvals",
                    change_type="evaluation_loop",
                    rationale="The deterministic evaluator found no blocking workflow issues in this run.",
                    expected_impact="Improves calibration data for future critic scoring",
                    before="Approval outcomes are not part of optimization feedback.",
                    after="Approval outcomes are logged and used to tune escalation thresholds.",
                    priority="LOW",
                    target_agent="Critic / Evaluator Agent",
                    problem="The system needs approval outcome labels to improve future threshold tuning.",
                    root_cause="Human approval results are not yet captured as evaluation feedback.",
                    fix="Log approval outcome, reviewer role, and reason code for every sensitive recommendation.",
                    expected_metric_lift={"policy_compliance": "+0.04", "escalation_quality": "+0.04"},
                    implementation_hint="Add approval_outcome fields to persisted run metadata when human review is implemented.",
                )
            )

        return recommendations

