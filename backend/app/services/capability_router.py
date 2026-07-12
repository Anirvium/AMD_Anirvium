from __future__ import annotations

from collections import Counter
import hashlib
import re
from typing import Any, Dict, Iterable, List

from app.schemas.capability import CapabilityRoute, DirectCapabilityResult
from app.services.intent_router import resolve_customer_support_intent
from app.services.llm_client import LLMClient, build_llm_client
from app.services.relational_store import RelationalRepository, get_relational_repository


_CUSTOMER_ID_RE = re.compile(r"\bCS-C\d{3,}\b", re.IGNORECASE)
_CRM_ID_RE = re.compile(r"\bCRM-CS-\d{3,}\b", re.IGNORECASE)
_CASE_ID_RE = re.compile(r"\b(?:CASE-[A-Z0-9-]+|(?<!CRM-)CS-\d{3,})\b", re.IGNORECASE)
_ANALYTICS_RE = re.compile(
    r"\b(how many|count|breakdown|distribution|analytics?|analyse|analyze|summary|rate|percentage|"
    r"most common|top issue|aggregate|statistics?)\b",
    re.IGNORECASE,
)
_LIST_RE = re.compile(r"\b(list|show|display|give me|which|all)\b", re.IGNORECASE)
_CUSTOMER_LOOKUP_RE = re.compile(
    r"\b(get|find|lookup|look up)\b.*\b(customer|profile)\b|\b(customer|profile)\b.*\b(details?|record)\b|\bshow customer\b",
    re.IGNORECASE,
)
_CASE_LOOKUP_RE = re.compile(
    r"\b(get|find|lookup|look up)\b.*\b(case|ticket)\b|\b(case|ticket)\b.*\b(details?|record)\b|\bshow case\b",
    re.IGNORECASE,
)
_PAYMENT_RE = re.compile(r"\b(payment|deposit|withdrawal|withdraw|upi|bank transfer)\b", re.IGNORECASE)
_CASE_RE = re.compile(r"\b(case|cases|ticket|tickets|failure|failures|issue|issues)\b", re.IGNORECASE)
_CUSTOMER_RE = re.compile(r"\b(customer|customers|profile|profiles|account holder|account holders)\b", re.IGNORECASE)
_SOCIAL_RE = re.compile(
    r"\b(hi|hello|hey|good morning|good afternoon|good evening|thank you|thanks|goodbye|bye|"
    r"are you there|can you help me|that is all|that's all)\b",
    re.IGNORECASE,
)
_GENERAL_DEFINITION_RE = re.compile(
    r"^\s*(what|who) (is|are|was|were)\b|^\s*(explain|define|describe)\b|\bhow does .+ work\??\s*$",
    re.IGNORECASE,
)
_PERSONAL_SUPPORT_PROBLEM_RE = re.compile(
    r"\b(my|mine|our|account|case|ticket|missing|not received|not showing|pending|failed|blocked|restricted|"
    r"unblock|refund|restore|release|complaint|manager|escalate|urgent|again|still)\b",
    re.IGNORECASE,
)

_PAYMENT_ISSUE_TYPES = ("deposit_missing", "withdrawal_processed_missing")
_SUPPORT_KINDS = {"SUPPORT_QUERY", "FOLLOW_UP", "COMPLAINT", "ESCALATION_REQUEST"}

_STATUS_PATTERNS = (
    (re.compile(r"\bwaiting(?:\s+for|_for)[\s_-]+customer\b", re.IGNORECASE), "WAITING_FOR_CUSTOMER"),
    (re.compile(r"\bin[\s_-]+progress\b", re.IGNORECASE), "IN_PROGRESS"),
    (re.compile(r"\bescalated\b", re.IGNORECASE), "ESCALATED"),
    (re.compile(r"\bresolved\b", re.IGNORECASE), "RESOLVED"),
    (re.compile(r"\bclosed\b", re.IGNORECASE), "CLOSED"),
    (re.compile(r"\bopen\b", re.IGNORECASE), "OPEN"),
)

_QUEUE_PATTERNS = (
    (re.compile(r"\b(financial operations|finance (?:operations|queue)|financial queue)\b", re.IGNORECASE), "financial_operations"),
    (re.compile(r"\b(verification (?:team|queue)|kyc (?:team|queue))\b", re.IGNORECASE), "verification_team"),
    (re.compile(r"\b(account security|account access queue)\b", re.IGNORECASE), "account_security"),
    (re.compile(r"\b(priority support|priority queue)\b", re.IGNORECASE), "priority_support"),
    (re.compile(r"\b(bonus support|bonus queue)\b", re.IGNORECASE), "bonus_support"),
    (re.compile(r"\b(billing operations|billing queue)\b", re.IGNORECASE), "billing_operations"),
    (re.compile(r"\b(support operations|general support queue)\b", re.IGNORECASE), "support_operations"),
    (
        re.compile(r"\b(engineering incident response|incident response queue|incident queue)\b", re.IGNORECASE),
        "engineering_incident_response",
    ),
    (re.compile(r"\b(engineering integrations|integration queue)\b", re.IGNORECASE), "engineering_integrations"),
    (re.compile(r"\bcustomer success(?: queue)?\b", re.IGNORECASE), "customer_success"),
    (re.compile(r"\b(security operations|security queue)\b", re.IGNORECASE), "security_operations"),
)

_ISSUE_TYPE_PATTERNS = (
    (re.compile(r"\b(deposit|upi deposit)\b", re.IGNORECASE), "deposit_missing"),
    (re.compile(r"\b(withdrawal|withdraw)\b", re.IGNORECASE), "withdrawal_processed_missing"),
    (re.compile(r"\b(verification|kyc)\b", re.IGNORECASE), "verification_restriction"),
    (re.compile(r"\bbonus\b", re.IGNORECASE), "bonus_dispute"),
    (re.compile(r"\b(cross[\s-]?account|another account|account access)\b", re.IGNORECASE), "cross_account_access"),
    (re.compile(r"\b(policy exception|priority exception)\b", re.IGNORECASE), "priority_policy_exception"),
    (re.compile(r"\b(billing|refund)\b", re.IGNORECASE), "billing_refund"),
    (re.compile(r"\b(production outage|outage)\b", re.IGNORECASE), "production_outage"),
    (re.compile(r"\bintegration(?: failure)?\b", re.IGNORECASE), "integration_failure"),
    (re.compile(r"\b(data deletion|delete (?:my )?data)\b", re.IGNORECASE), "security_data_deletion"),
    (re.compile(r"\bchurn\b", re.IGNORECASE), "churn_risk"),
    (re.compile(r"\bfeature request\b", re.IGNORECASE), "feature_request"),
    (re.compile(r"\b(duplicate|low priority)\b", re.IGNORECASE), "duplicate_low_priority"),
)


def _route_id(query: str, capability: str) -> str:
    digest = hashlib.sha256(f"{capability}:{query.strip().lower()}".encode("utf-8")).hexdigest()[:12]
    return f"route_{digest}"


class CapabilityRouter:
    """Routes a user turn without weakening the governed support workflow.

    Business-data capabilities are read-only queries over the relational
    repository. Customer support problems continue through the existing
    Sarvagun agent pipeline. General public knowledge is the only direct path
    that may call the configured language model.
    """

    def __init__(
        self,
        repository: RelationalRepository | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.repository = repository or get_relational_repository()
        self.llm_client = llm_client or build_llm_client()

    def route(
        self,
        query: str,
        *,
        conversation_kind: str,
        conversation_requires_agent: bool,
    ) -> CapabilityRoute:
        normalized = " ".join(query.strip().lower().split())
        customer_reference = self._extract_customer_reference(query)
        case_reference = self._extract_case_reference(query)
        analytical = bool(_ANALYTICS_RE.search(normalized))
        payment_related = bool(_PAYMENT_RE.search(normalized))
        case_related = bool(_CASE_RE.search(normalized))
        customer_related = bool(_CUSTOMER_RE.search(normalized))
        list_requested = bool(_LIST_RE.search(normalized))

        # A typed case id is unambiguous even in concise commands such as
        # ``Open CS-001``. Customer ids use the distinct CS-C### shape.
        if case_reference:
            return self._route(
                query,
                "case_lookup",
                "direct_relational_read",
                0.99,
                "An explicit support case reference was requested.",
                ["case_lookup_operator", case_reference],
                data_scope="synthetic_support_case_records",
            )
        if analytical:
            signals = ["analytical_operator"]
            if payment_related:
                signals.append("payment_domain")
            if customer_related:
                signals.append("customer_domain")
            return self._route(
                query,
                "support_analytics",
                "deterministic_analytics",
                0.96,
                "The request asks for an aggregate or computed support metric.",
                signals,
                data_scope="synthetic_customer_and_case_aggregates",
            )
        if list_requested and payment_related and case_related:
            return self._route(
                query,
                "payment_failure_cases",
                "direct_relational_read",
                0.97,
                "The request asks for payment-related support case records.",
                ["list_operator", "payment_domain", "case_domain"],
                data_scope="synthetic_support_case_records",
            )
        if _CASE_LOOKUP_RE.search(normalized):
            return self._route(
                query,
                "case_lookup",
                "direct_relational_read",
                0.95,
                "A support case detail lookup was requested.",
                ["case_lookup_operator", "case_details_reference"],
                data_scope="synthetic_support_case_records",
            )
        if list_requested and case_related:
            signals = ["list_operator", "case_domain"]
            if self._extract_status(query):
                signals.append("status_filter")
            if self._extract_queue(query):
                signals.append("queue_filter")
            if customer_reference:
                signals.append("customer_filter")
            return self._route(
                query,
                "case_directory",
                "direct_relational_read",
                0.97,
                "The request asks for support case records with optional relational filters.",
                signals,
                data_scope="synthetic_support_case_records",
            )
        if customer_related and (customer_reference or _CUSTOMER_LOOKUP_RE.search(normalized)):
            return self._route(
                query,
                "customer_lookup",
                "direct_relational_read",
                0.99,
                "An explicit customer reference was requested.",
                ["customer_lookup_operator", customer_reference or "name_or_profile_reference"],
                data_scope="synthetic_customer_records",
            )
        if list_requested and customer_related:
            return self._route(
                query,
                "customer_directory",
                "direct_relational_read",
                0.97,
                "The request asks for the customer directory.",
                ["list_operator", "customer_domain"],
                data_scope="synthetic_customer_records",
            )

        if _GENERAL_DEFINITION_RE.search(normalized) and not _PERSONAL_SUPPORT_PROBLEM_RE.search(normalized):
            return self._route(
                query,
                "general_knowledge",
                "general_knowledge_llm",
                0.93,
                "The request is a public definitional question without a personal support problem.",
                ["definition_question", "no_personal_support_signal"],
                data_scope="public_general_knowledge_only",
            )

        support_intent = resolve_customer_support_intent(query)
        if support_intent is not None or conversation_requires_agent or conversation_kind in _SUPPORT_KINDS:
            signals = ["conversation_support_signal"]
            if support_intent:
                signals.extend(["support_intent", support_intent.issue_type])
            return CapabilityRoute(
                route_id=_route_id(query, "support_case_execution"),
                capability="support_case_execution",
                execution_path="sarvagun_agent_pipeline",
                requires_agent_run=True,
                confidence=support_intent.confidence if support_intent else 0.86,
                reason="The request requires the governed Sarvagun support workflow.",
                matched_signals=signals,
                read_only=False,
                data_scope="selected_customer_support_case",
            )

        if conversation_kind != "SMALL_TALK" or _SOCIAL_RE.search(normalized):
            return self._route(
                query,
                "conversation_fast_path",
                "conversation_manager",
                0.96,
                "The turn is a conversational transition that does not require retrieval or tools.",
                [f"conversation_kind:{conversation_kind}"],
            )

        return self._route(
            query,
            "general_knowledge",
            "general_knowledge_llm",
            0.82,
            "The request is neither a customer-support action nor a business-record query.",
            ["open_domain_question"],
            data_scope="public_general_knowledge_only",
        )

    def execute(self, route: CapabilityRoute, query: str) -> DirectCapabilityResult | None:
        capability = route.capability
        if capability in {"support_case_execution", "conversation_fast_path"}:
            return None
        try:
            if capability == "customer_directory":
                return self._list_customers(query)
            if capability == "payment_failure_cases":
                return self._list_payment_failure_cases(query)
            if capability == "customer_lookup":
                return self._get_customer(query)
            if capability == "case_directory":
                return self._list_cases(query)
            if capability == "case_lookup":
                return self._get_case(query)
            if capability == "support_analytics":
                return self._analytics(query)
            if capability == "general_knowledge":
                return self._general_knowledge(query)
        except Exception as exc:
            return DirectCapabilityResult(
                capability=capability,
                status="degraded",
                answer="I routed the request correctly, but the read-only capability could not complete. No support action or data write was attempted.",
                generated_by="capability_router_safe_fallback",
                fallback_reason=f"{type(exc).__name__}: {exc}",
                synthetic_data_only=capability != "general_knowledge",
            )
        return None

    def _route(
        self,
        query: str,
        capability: str,
        execution_path: str,
        confidence: float,
        reason: str,
        signals: List[str],
        *,
        data_scope: str = "none",
    ) -> CapabilityRoute:
        return CapabilityRoute(
            route_id=_route_id(query, capability),
            capability=capability,  # type: ignore[arg-type]
            execution_path=execution_path,  # type: ignore[arg-type]
            requires_agent_run=False,
            confidence=confidence,
            reason=reason,
            matched_signals=signals,
            read_only=True,
            data_scope=data_scope,
        )

    def _list_customers(self, query: str) -> DirectCapabilityResult:
        plan = self._extract_filter(query, ("free", "pro", "business", "enterprise"))
        region = "IN" if re.search(r"\b(india|in region|region in)\b", query, re.IGNORECASE) else None
        customers = [self._public_customer(row) for row in self.repository.list_customers(plan=plan, region=region)]
        qualifier = ""
        if plan:
            qualifier = f" on the {plan} plan"
        if region:
            qualifier += f" in region {region}"
        names = ", ".join(f"{item['customer_name']} ({item['customer_id']})" for item in customers)
        answer = (
            f"I found {len(customers)} seeded customers{qualifier}: {names}."
            if customers
            else f"No seeded customers matched the requested filters{qualifier}."
        )
        return DirectCapabilityResult(
            capability="customer_directory",
            status="success" if customers else "not_found",
            answer=answer,
            record_count=len(customers),
            records=customers,
            aggregates={"plan_filter": plan, "region_filter": region},
            source_ids=["relational.customers"],
            generated_by="deterministic_relational_query",
        )

    def _list_payment_failure_cases(self, query: str) -> DirectCapabilityResult:
        status = self._extract_status(query)
        queue = self._extract_queue(query)
        customer_id = self._resolve_customer_id(query)
        requested_issue_type = self._extract_issue_type(query)
        issue_types = (
            (requested_issue_type,)
            if requested_issue_type in _PAYMENT_ISSUE_TYPES
            else _PAYMENT_ISSUE_TYPES
        )
        rows: Dict[str, Dict[str, Any]] = {}
        for issue_type in issue_types:
            for row in self.repository.list_cases(
                issue_type=issue_type,
                status=status,
                queue=queue,
                customer_id=customer_id,
                limit=500,
            ):
                public = self._public_case(row)
                rows[str(public["case_id"])] = public
        cases = sorted(rows.values(), key=lambda item: str(item.get("contacted_at") or ""), reverse=True)
        answer = (
            f"I found {len(cases)} seeded payment-failure cases: "
            + ", ".join(f"{row['case_id']} ({row['issue_type']}, {row['status']})" for row in cases)
            + "."
            if cases
            else "No seeded deposit-missing or withdrawal-missing cases were found."
        )
        return DirectCapabilityResult(
            capability="payment_failure_cases",
            status="success" if cases else "not_found",
            answer=answer,
            record_count=len(cases),
            records=cases,
            aggregates={
                "issue_types": list(issue_types),
                "status_filter": status,
                "queue_filter": queue,
                "customer_id_filter": customer_id,
            },
            source_ids=["relational.support_cases"],
            generated_by="deterministic_relational_query",
        )

    def _list_cases(self, query: str) -> DirectCapabilityResult:
        issue_type = self._extract_issue_type(query)
        status = self._extract_status(query)
        queue = self._extract_queue(query)
        customer_id = self._resolve_customer_id(query)
        cases = [
            self._public_case(row)
            for row in self.repository.list_cases(
                issue_type=issue_type,
                status=status,
                queue=queue,
                customer_id=customer_id,
                limit=500,
            )
        ]
        answer = (
            f"I found {len(cases)} seeded support cases: "
            + ", ".join(
                f"{row['case_id']} ({row['issue_type']}, {row['status']}, {row['queue']})"
                for row in cases
            )
            + "."
            if cases
            else "No seeded support cases matched the requested filters."
        )
        return DirectCapabilityResult(
            capability="case_directory",
            status="success" if cases else "not_found",
            answer=answer,
            record_count=len(cases),
            records=cases,
            aggregates={
                "issue_type_filter": issue_type,
                "status_filter": status,
                "queue_filter": queue,
                "customer_id_filter": customer_id,
            },
            source_ids=["relational.support_cases"],
            generated_by="deterministic_relational_query",
        )

    def _get_customer(self, query: str) -> DirectCapabilityResult:
        reference = self._extract_customer_reference(query)
        customer = self.repository.get_customer(reference) if reference and reference.upper().startswith("CS-C") else None
        if customer is None:
            normalized = query.lower()
            customer = next(
                (
                    row
                    for row in self.repository.list_customers()
                    if str(row.get("crm_account_id", "")).lower() in normalized
                    or str(row.get("customer_name", "")).lower() in normalized
                ),
                None,
            )
        if customer is None:
            return DirectCapabilityResult(
                capability="customer_lookup",
                status="not_found",
                answer=f"No seeded customer matched {reference or 'the supplied reference'}.",
                generated_by="deterministic_relational_query",
                source_ids=["relational.customers"],
            )
        public = self._public_customer(customer)
        related_cases = [
            self._public_case(row)
            for row in self.repository.list_cases(customer_id=str(public["customer_id"]))
        ]
        return DirectCapabilityResult(
            capability="customer_lookup",
            status="success",
            answer=(
                f"{public['customer_name']} ({public['customer_id']}) is on the {public.get('plan', 'unknown')} plan "
                f"in region {public.get('region', 'unknown')} and has {len(related_cases)} seeded case records."
            ),
            record_count=1,
            records=[public],
            aggregates={"related_case_count": len(related_cases), "related_cases": related_cases},
            source_ids=[f"relational.customer:{public['customer_id']}", "relational.support_cases"],
            generated_by="deterministic_relational_query",
        )

    def _get_case(self, query: str) -> DirectCapabilityResult:
        reference = self._extract_case_reference(query)
        case = self.repository.get_case(reference) if reference else None
        if case is None:
            return DirectCapabilityResult(
                capability="case_lookup",
                status="not_found",
                answer=f"No seeded support case matched {reference or 'the supplied reference'}.",
                generated_by="deterministic_relational_query",
                source_ids=["relational.support_cases"],
            )
        public = self._public_case(case)
        return DirectCapabilityResult(
            capability="case_lookup",
            status="success",
            answer=(
                f"Case {public['case_id']} belongs to {public.get('customer_name') or public.get('customer_id')}, "
                f"is classified as {public.get('issue_type')}, has status {public.get('status')}, "
                f"and is routed to {public.get('queue') or 'the support queue'}."
            ),
            record_count=1,
            records=[public],
            source_ids=[f"relational.case:{public['case_id']}"],
            generated_by="deterministic_relational_query",
        )

    def _analytics(self, query: str) -> DirectCapabilityResult:
        issue_type = self._extract_issue_type(query)
        status = self._extract_status(query)
        queue = self._extract_queue(query)
        customer_id = self._resolve_customer_id(query)
        customers = [self._public_customer(row) for row in self.repository.list_customers(limit=500)]
        cases = [
            self._public_case(row)
            for row in self.repository.list_cases(
                issue_type=issue_type,
                status=status,
                queue=queue,
                customer_id=customer_id,
                limit=500,
            )
        ]
        issue_counts = Counter(str(row.get("issue_type") or "unknown") for row in cases)
        status_counts = Counter(str(row.get("status") or "unknown") for row in cases)
        priority_counts = Counter(str(row.get("priority") or "unknown") for row in cases)
        plan_counts = Counter(str(row.get("plan") or "unknown") for row in customers)
        payment_cases = [row for row in cases if row.get("issue_type") in _PAYMENT_ISSUE_TYPES]
        recontact_groups = Counter(
            (str(row.get("customer_id")), str(row.get("issue_type")))
            for row in cases
            if row.get("customer_id") and row.get("issue_type")
        )
        recontact_customers = {customer_id for (customer_id, _), count in recontact_groups.items() if count > 1}
        aggregate = {
            "customer_count": len(customers),
            "case_count": len(cases),
            "payment_failure_case_count": len(payment_cases),
            "issue_type_breakdown": dict(sorted(issue_counts.items())),
            "status_breakdown": dict(sorted(status_counts.items())),
            "priority_breakdown": dict(sorted(priority_counts.items())),
            "customer_plan_breakdown": dict(sorted(plan_counts.items())),
            "recontact_customer_count": len(recontact_customers),
            "recontact_rate": round(len(recontact_customers) / max(1, len(customers)), 3),
            "issue_type_filter": issue_type,
            "status_filter": status,
            "queue_filter": queue,
            "customer_id_filter": customer_id,
        }
        normalized = query.lower()
        if _PAYMENT_RE.search(normalized):
            answer = (
                f"There are {len(payment_cases)} seeded payment-failure cases: "
                f"{sum(1 for row in payment_cases if row.get('issue_type') == 'deposit_missing')} deposit-missing and "
                f"{sum(1 for row in payment_cases if row.get('issue_type') == 'withdrawal_processed_missing')} withdrawal-missing cases."
            )
        elif "customer" in normalized and re.search(r"\b(how many|count|total)\b", normalized):
            answer = f"There are {len(customers)} customers in the seeded relational support dataset."
        elif "priority" in normalized:
            answer = "Case priority breakdown: " + self._format_counts(priority_counts) + "."
        elif "status" in normalized:
            answer = "Case status breakdown: " + self._format_counts(status_counts) + "."
        elif "plan" in normalized:
            answer = "Customer plan breakdown: " + self._format_counts(plan_counts) + "."
        elif "recontact" in normalized or "repeat" in normalized:
            answer = (
                f"{len(recontact_customers)} of {len(customers)} seeded customers have repeated records for the same issue; "
                f"the derived recontact rate is {aggregate['recontact_rate']:.1%}."
            )
        else:
            answer = (
                f"The seeded relational dataset contains {len(customers)} customers and {len(cases)} cases. "
                "Issue breakdown: " + self._format_counts(issue_counts) + "."
            )
        return DirectCapabilityResult(
            capability="support_analytics",
            status="success",
            answer=answer,
            record_count=len(cases),
            aggregates=aggregate,
            source_ids=["relational.customers", "relational.support_cases"],
            generated_by="deterministic_relational_analytics",
        )

    def _general_knowledge(self, query: str) -> DirectCapabilityResult:
        model_name = getattr(self.llm_client, "model_name", "mock-trajectory-model")
        if model_name == "mock-trajectory-model":
            return DirectCapabilityResult(
                capability="general_knowledge",
                status="degraded",
                answer=(
                    "I classified this as a general-knowledge question, but no live language model is configured in this runtime. "
                    "Connect the AMD vLLM endpoint to receive a model-generated answer."
                ),
                generated_by="truthful_deterministic_fallback",
                fallback_reason="live_llm_not_configured",
                synthetic_data_only=False,
            )
        if re.search(r"\b(latest|today|currently|current news|live price|real-time)\b", query, re.IGNORECASE):
            return DirectCapabilityResult(
                capability="general_knowledge",
                status="degraded",
                answer=(
                    "This asks for time-sensitive information. Sarvagun has no live web-search source in this runtime, "
                    "so I cannot verify a current answer safely."
                ),
                generated_by="truthful_deterministic_fallback",
                fallback_reason="live_source_required",
                synthetic_data_only=False,
            )
        try:
            response = self.llm_client.generate(
                [
                    {
                        "role": "system",
                        "content": (
                            "Answer the public general-knowledge question concisely and accurately. "
                            "Do not claim to have used customer records, enterprise tools, live web search, or current data. "
                            "If uncertain, state the uncertainty. Return only the answer, never hidden reasoning."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.1,
            )
        except Exception as exc:
            return DirectCapabilityResult(
                capability="general_knowledge",
                status="degraded",
                answer="The general-knowledge model call failed, so I did not invent an answer. Please retry after checking the AMD model runtime.",
                generated_by="truthful_deterministic_fallback",
                fallback_reason=f"{type(exc).__name__}: {exc}",
                synthetic_data_only=False,
            )
        text = response.text.strip()
        if not text:
            return DirectCapabilityResult(
                capability="general_knowledge",
                status="degraded",
                answer="The model returned no public answer. I did not substitute an unverified response.",
                generated_by="truthful_deterministic_fallback",
                fallback_reason="empty_public_model_output",
                synthetic_data_only=False,
            )
        return DirectCapabilityResult(
            capability="general_knowledge",
            status="success",
            answer=text,
            record_count=0,
            source_ids=[],
            generated_by=f"live_llm:{response.model_name}",
            synthetic_data_only=False,
        )

    def _extract_customer_reference(self, query: str) -> str | None:
        match = _CUSTOMER_ID_RE.search(query) or _CRM_ID_RE.search(query)
        return match.group(0).upper() if match else None

    def _extract_case_reference(self, query: str) -> str | None:
        match = _CASE_ID_RE.search(query)
        return match.group(0).upper() if match else None

    def _extract_status(self, query: str) -> str | None:
        return next((status for pattern, status in _STATUS_PATTERNS if pattern.search(query)), None)

    def _extract_queue(self, query: str) -> str | None:
        return next((queue for pattern, queue in _QUEUE_PATTERNS if pattern.search(query)), None)

    def _extract_issue_type(self, query: str) -> str | None:
        return next((issue_type for pattern, issue_type in _ISSUE_TYPE_PATTERNS if pattern.search(query)), None)

    def _resolve_customer_id(self, query: str) -> str | None:
        reference = self._extract_customer_reference(query)
        if not reference:
            return None
        if reference.startswith("CS-C"):
            return reference
        return next(
            (
                str(row["customer_id"])
                for row in self.repository.list_customers(limit=500)
                if str(row.get("crm_account_id", "")).upper() == reference
            ),
            None,
        )

    def _extract_filter(self, query: str, values: Iterable[str]) -> str | None:
        normalized = query.lower()
        return next((value for value in values if re.search(rf"\b{re.escape(value)}\b", normalized)), None)

    def _public_customer(self, row: Dict[str, Any]) -> Dict[str, Any]:
        fields = (
            "customer_id",
            "customer_name",
            "plan",
            "region",
            "preferred_channel",
            "identity_status",
            "crm_account_id",
        )
        return {field: row.get(field) for field in fields if row.get(field) is not None}

    def _public_case(self, row: Dict[str, Any]) -> Dict[str, Any]:
        fields = (
            "case_id",
            "customer_id",
            "customer_name",
            "issue_type",
            "status",
            "queue",
            "priority",
            "contacted_at",
            "transaction_id",
            "commitment_deadline",
            "commitment_met",
        )
        return {field: row.get(field) for field in fields if row.get(field) is not None}

    def _format_counts(self, counts: Counter[str]) -> str:
        return ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"


capability_router = CapabilityRouter()
