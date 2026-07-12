from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Mapping

from app.config import get_settings
from app.services.data_loader import load_cx_context, load_tickets
from app.services.knowledge_base import load_kb_layer


SCHEMA_VERSION = "sarvagun-operational-v1"
SYNTHETIC_EVALUATION_SUITE = "sarvagun-curated-eval-v1"

_QUEUE_BY_ISSUE = {
    "billing_refund": "billing_operations",
    "bonus_dispute": "bonus_support",
    "cross_account_access": "account_security",
    "deposit_missing": "financial_operations",
    "integration_failure": "engineering_integrations",
    "priority_policy_exception": "priority_support",
    "production_outage": "engineering_incident_response",
    "security_data_deletion": "security_operations",
    "verification_restriction": "verification_team",
    "withdrawal_processed_missing": "financial_operations",
}

_QUEUE_ROWS = (
    ("account_security", "Account Security", "account_access", "security_reviewer"),
    ("billing_operations", "Billing Operations", "billing", "billing_approver"),
    ("bonus_support", "Bonus Support", "bonuses", "bonus_policy_reviewer"),
    ("customer_success", "Customer Success", "retention", "customer_success_manager"),
    ("engineering_incident_response", "Engineering Incident Response", "incidents", "incident_commander"),
    ("engineering_integrations", "Engineering Integrations", "integrations", "integration_engineer"),
    ("financial_operations", "Financial Operations", "payments", "finance_supervisor"),
    ("priority_support", "Priority Support", "priority_support", "authorized_approver"),
    ("security_operations", "Security Operations", "security", "security_lead"),
    ("senior_support", "Senior Support", "general_support", "senior_support_manager"),
    ("support_operations", "Support Operations", "general_support", "support_manager"),
    ("verification_team", "Verification Team", "verification", "verification_reviewer"),
)

_ACCOUNT_ROWS = (
    ("ACC-CS-001", "CS-C001", "wallet", "INR", "ACTIVE", "verified", "2024-01-15T00:00:00Z"),
    ("ACC-CS-002", "CS-C002", "wallet", "INR", "ACTIVE", "verified", "2024-03-09T00:00:00Z"),
    ("ACC-CS-003", "CS-C003", "wallet", "INR", "RESTRICTED", "review_pending", "2024-04-21T00:00:00Z"),
    ("ACC-CS-004", "CS-C004", "wallet", "INR", "ACTIVE", "verified", "2025-01-08T00:00:00Z"),
    ("ACC-CS-005", "CS-C005", "wallet", "INR", "LIMITED", "channel_unverified", "2025-02-17T00:00:00Z"),
    ("ACC-CS-006", "CS-C006", "priority_wallet", "INR", "RESTRICTED", "review_pending", "2023-11-02T00:00:00Z"),
)

_TRANSACTION_ROWS = (
    ("TXN-DEP-7781", "DEP-7781", "CS-C001", "ACC-CS-001", "CS-001", "deposit", "UPI", 12500.0, "INR", "payment_evidence_received", 0, "2026-07-11T09:35:00Z"),
    ("TXN-WDR-2291", "WDR-2291", "CS-C002", "ACC-CS-002", "CS-002", "withdrawal", "bank_transfer", 24000.0, "INR", "bank_trace_under_review", 0, "2026-07-11T09:42:00Z"),
    ("TXN-BONUS-118", "BONUS-118", "CS-C004", "ACC-CS-004", "CS-004", "bonus", "promotion", 1500.0, "INR", "eligibility_review_required", 0, "2026-07-11T08:55:00Z"),
    ("TXN-WDR-PRIORITY-901", "PRIORITY-901", "CS-C006", "ACC-CS-006", "CS-006", "withdrawal", "bank_transfer", 50000.0, "INR", "blocked_by_verification", 0, "2026-07-11T09:05:00Z"),
    ("TXN-PAY-701", "DEP-HIST-701", "CS-C001", "ACC-CS-001", "CASE-DEP-701", "payment", "UPI", 12500.0, "INR", "financial_review_in_progress", 0, "2026-07-10T08:20:00Z"),
)

_VERIFICATION_ROWS = (
    ("VER-CS-001", "CS-C001", "ACC-CS-001", None, "verified", "identity_and_payment_profile", None, "2026-06-01T00:00:00Z"),
    ("VER-CS-002", "CS-C002", "ACC-CS-002", None, "verified", "identity_and_bank_profile", None, "2026-06-14T00:00:00Z"),
    ("VER-CS-003", "CS-C003", "ACC-CS-003", "CS-003", "review_pending", "kyc_reverification", "address_proof,selfie", "2026-07-11T08:20:00Z"),
    ("VER-CS-004", "CS-C004", "ACC-CS-004", None, "verified", "identity_profile", None, "2026-05-19T00:00:00Z"),
    ("VER-CS-005", "CS-C005", "ACC-CS-005", "CS-005", "channel_unverified", "registered_channel", "registered_email_confirmation", "2026-07-11T08:25:00Z"),
    ("VER-CS-006", "CS-C006", "ACC-CS-006", "CS-006", "review_pending", "priority_account_reverification", "source_of_funds", "2026-07-11T08:30:00Z"),
)

_APPROVAL_ROWS = (
    ("APR-CS-001", "CS-C001", "CS-001", "TXN-DEP-7781", "financial_review", "finance_supervisor", "PENDING", "2026-07-11T09:36:00Z"),
    ("APR-CS-002", "CS-C002", "CS-002", "TXN-WDR-2291", "withdrawal_trace", "finance_supervisor", "PENDING", "2026-07-11T09:43:00Z"),
    ("APR-CS-003", "CS-C003", "CS-003", None, "restriction_removal", "verification_reviewer", "REQUIRED", "2026-07-11T08:21:00Z"),
    ("APR-CS-004", "CS-C004", "CS-004", "TXN-BONUS-118", "bonus_exception", "bonus_policy_reviewer", "REQUIRED", "2026-07-11T08:56:00Z"),
    ("APR-CS-005", "CS-C005", "CS-005", None, "cross_account_disclosure", "security_reviewer", "REQUIRED", "2026-07-11T08:26:00Z"),
    ("APR-CS-006", "CS-C006", "CS-006", "TXN-WDR-PRIORITY-901", "policy_exception", "authorized_approver", "REQUIRED", "2026-07-11T09:06:00Z"),
)

_ESCALATION_ROWS = (
    ("ESC-CS-001", "CS-C001", "CS-001", "APR-CS-001", "payment_window_elapsed", "financial_operations", "high", 60, "IN_PROGRESS", "2026-07-11T09:37:00Z"),
    ("ESC-CS-002", "CS-C002", "CS-002", "APR-CS-002", "third_contact_same_issue", "senior_support", "high", 30, "ESCALATED", "2026-07-11T09:44:00Z"),
    ("ESC-CS-003", "CS-C003", "CS-003", "APR-CS-003", "verification_restriction", "verification_team", "high", 30, "APPROVAL_REQUIRED", "2026-07-11T08:22:00Z"),
    ("ESC-CS-005", "CS-C005", "CS-005", "APR-CS-005", "unverified_cross_account_request", "account_security", "high", 15, "APPROVAL_REQUIRED", "2026-07-11T08:27:00Z"),
    ("ESC-CS-006", "CS-C006", "CS-006", "APR-CS-006", "priority_policy_exception", "priority_support", "critical", 15, "APPROVAL_REQUIRED", "2026-07-11T09:07:00Z"),
)

_WORKFLOW_ROWS = (
    ("WF-CS-001-01", "CS-001", "transaction", "TXN-DEP-7781", "RECEIVED", 1, "2026-07-11T09:34:00Z", "Sarvagun", {"evidence": "payment screenshot"}),
    ("WF-CS-001-02", "CS-001", "transaction", "TXN-DEP-7781", "EVIDENCE_RETRIEVED", 2, "2026-07-11T09:35:00Z", "Sarvagun", {"policy": "POL-CS-PAY-001"}),
    ("WF-CS-001-03", "CS-001", "transaction", "TXN-DEP-7781", "FINANCIAL_REVIEW", 3, "2026-07-11T09:37:00Z", "finance_supervisor", {"approval": "APR-CS-001"}),
    ("WF-CS-002-01", "CS-002", "transaction", "TXN-WDR-2291", "RECEIVED", 1, "2026-07-11T09:40:00Z", "Sarvagun", {"contact_number": 3}),
    ("WF-CS-002-02", "CS-002", "transaction", "TXN-WDR-2291", "RECONTACT_DETECTED", 2, "2026-07-11T09:41:00Z", "SuperTuriya", {"related_cases": ["CASE-WDR-881", "CASE-WDR-912"]}),
    ("WF-CS-002-03", "CS-002", "transaction", "TXN-WDR-2291", "ESCALATED", 3, "2026-07-11T09:44:00Z", "senior_support", {"escalation": "ESC-CS-002"}),
    ("WF-CS-003-01", "CS-003", "verification", "VER-CS-003", "DOCUMENTS_REQUIRED", 1, "2026-07-11T08:20:00Z", "verification_team", {"missing": ["address_proof", "selfie"]}),
    ("WF-CS-003-02", "CS-003", "verification", "VER-CS-003", "APPROVAL_REQUIRED", 2, "2026-07-11T08:22:00Z", "verification_reviewer", {"approval": "APR-CS-003"}),
    ("WF-CS-004-01", "CS-004", "transaction", "TXN-BONUS-118", "ELIGIBILITY_REVIEW", 1, "2026-07-11T08:55:00Z", "bonus_support", {"approval": "APR-CS-004"}),
    ("WF-CS-005-01", "CS-005", "verification", "VER-CS-005", "REGISTERED_CHANNEL_REQUIRED", 1, "2026-07-11T08:25:00Z", "account_security", {"policy": "POL-CS-ACCESS-001"}),
    ("WF-CS-005-02", "CS-005", "verification", "VER-CS-005", "APPROVAL_REQUIRED", 2, "2026-07-11T08:27:00Z", "security_reviewer", {"approval": "APR-CS-005"}),
    ("WF-CS-006-01", "CS-006", "approval", "APR-CS-006", "POLICY_GATE_ACTIVE", 1, "2026-07-11T09:05:00Z", "Sarvagun", {"bypass_allowed": False}),
    ("WF-CS-006-02", "CS-006", "approval", "APR-CS-006", "AUTHORIZED_APPROVER_REVIEW", 2, "2026-07-11T09:07:00Z", "priority_support", {"escalation": "ESC-CS-006"}),
)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _bounded_limit(limit: int) -> int:
    return max(1, min(int(limit), 500))


def _commitment_value(value: Any) -> int | None:
    if value is None:
        return None
    return 1 if bool(value) else 0


def _row_dict(row: sqlite3.Row | None) -> Dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    if "commitment_met" in item and item["commitment_met"] is not None:
        item["commitment_met"] = bool(item["commitment_met"])
    if "outcome_confirmed" in item and item["outcome_confirmed"] is not None:
        item["outcome_confirmed"] = bool(item["outcome_confirmed"])
    if "simulated" in item and item["simulated"] is not None:
        item["simulated"] = bool(item["simulated"])
    return item


class RelationalRepository:
    """SQLite-backed operational truth for structured support data.

    Semantic KB and trajectory recall remain in the vector store. Redis remains
    the short-lived session cache. This repository persists normalized business
    facts that require exact filtering, foreign keys, and idempotent writes.
    """

    def __init__(self, database_path: str | Path, *, seed: bool = True) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = Lock()
        self._initialize_schema()
        if seed:
            self.seed_synthetic_data()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize_schema(self) -> None:
        with self._write_lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS support_queues (
                    queue TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    approval_role TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    region TEXT NOT NULL,
                    preferred_channel TEXT NOT NULL,
                    identity_status TEXT NOT NULL,
                    crm_account_id TEXT UNIQUE,
                    source_fixture TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS support_cases (
                    case_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    issue_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    queue TEXT NOT NULL REFERENCES support_queues(queue),
                    priority TEXT NOT NULL,
                    contacted_at TEXT NOT NULL,
                    sla_deadline TEXT,
                    transaction_id TEXT,
                    commitment_deadline TEXT,
                    commitment_met INTEGER CHECK (commitment_met IN (0, 1) OR commitment_met IS NULL),
                    source_fixture TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_support_cases_customer ON support_cases(customer_id);
                CREATE INDEX IF NOT EXISTS idx_support_cases_filters ON support_cases(issue_type, status, queue);

                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    product TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    source_fixture TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id, status);

                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    reference TEXT NOT NULL UNIQUE,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    account_id TEXT NOT NULL REFERENCES accounts(account_id),
                    case_id TEXT REFERENCES support_cases(case_id),
                    transaction_type TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    amount REAL NOT NULL CHECK (amount >= 0),
                    currency TEXT NOT NULL,
                    state TEXT NOT NULL,
                    outcome_confirmed INTEGER NOT NULL CHECK (outcome_confirmed IN (0, 1)),
                    updated_at TEXT NOT NULL,
                    source_fixture TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_transactions_filters
                    ON transactions(customer_id, case_id, transaction_type, state);

                CREATE TABLE IF NOT EXISTS verification_records (
                    verification_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    account_id TEXT NOT NULL REFERENCES accounts(account_id),
                    case_id TEXT REFERENCES support_cases(case_id),
                    status TEXT NOT NULL,
                    verification_type TEXT NOT NULL,
                    missing_requirements TEXT,
                    reviewed_at TEXT NOT NULL,
                    source_fixture TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_verification_filters
                    ON verification_records(customer_id, case_id, status);

                CREATE TABLE IF NOT EXISTS approval_requests (
                    approval_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    case_id TEXT NOT NULL REFERENCES support_cases(case_id),
                    transaction_id TEXT REFERENCES transactions(transaction_id),
                    approval_type TEXT NOT NULL,
                    approver_role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    decided_at TEXT,
                    decision_reason TEXT,
                    source_fixture TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_approval_filters
                    ON approval_requests(case_id, approval_type, status);

                CREATE TABLE IF NOT EXISTS escalations (
                    escalation_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    case_id TEXT NOT NULL REFERENCES support_cases(case_id),
                    approval_id TEXT REFERENCES approval_requests(approval_id),
                    reason TEXT NOT NULL,
                    destination TEXT NOT NULL REFERENCES support_queues(queue),
                    severity TEXT NOT NULL,
                    sla_minutes INTEGER NOT NULL CHECK (sla_minutes > 0),
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    source_fixture TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_escalation_filters
                    ON escalations(case_id, destination, status);

                CREATE TABLE IF NOT EXISTS workflow_states (
                    workflow_state_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES support_cases(case_id),
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK (sequence > 0),
                    entered_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    source_fixture TEXT NOT NULL,
                    UNIQUE(case_id, entity_type, entity_id, sequence)
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_case_sequence
                    ON workflow_states(case_id, sequence);

                CREATE TABLE IF NOT EXISTS evaluation_cases (
                    evaluation_case_id TEXT PRIMARY KEY,
                    source_suite TEXT NOT NULL,
                    external_benchmark TEXT,
                    title TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    language TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    ticket TEXT NOT NULL,
                    expected_approval_state TEXT NOT NULL,
                    expected_route TEXT NOT NULL,
                    expected_evidence_json TEXT NOT NULL,
                    unsafe_outputs_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_evaluation_cases_domain ON evaluation_cases(domain, risk_level);

                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    conversation_id TEXT PRIMARY KEY,
                    customer_id TEXT REFERENCES customers(customer_id),
                    message_type TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                );

                CREATE TABLE IF NOT EXISTS conversation_turns (
                    turn_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivery_status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    conversation_id TEXT REFERENCES conversation_sessions(conversation_id),
                    customer_id TEXT REFERENCES customers(customer_id),
                    execution_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    resolution_stage TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evaluations (
                    run_id TEXT PRIMARY KEY REFERENCES agent_runs(run_id) ON DELETE CASCADE,
                    overall_score REAL NOT NULL,
                    metrics_json TEXT NOT NULL,
                    diagnosis_json TEXT NOT NULL,
                    recommendations_json TEXT NOT NULL,
                    predicted_satisfaction REAL,
                    predicted_label TEXT,
                    response_quality_score REAL
                );

                CREATE TABLE IF NOT EXISTS tool_executions (
                    tool_execution_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES agent_runs(run_id) ON DELETE CASCADE,
                    operation TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    authorization TEXT NOT NULL,
                    audit_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    latency_ms INTEGER NOT NULL,
                    simulated INTEGER NOT NULL CHECK (simulated IN (0, 1)),
                    result_json TEXT NOT NULL,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS explicit_feedback (
                    run_id TEXT PRIMARY KEY REFERENCES agent_runs(run_id) ON DELETE CASCADE,
                    explicit_csat INTEGER NOT NULL CHECK (explicit_csat BETWEEN 1 AND 5),
                    explicit_resolution TEXT NOT NULL CHECK (explicit_resolution IN ('yes', 'partially', 'no')),
                    recorded_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO schema_metadata(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (SCHEMA_VERSION,),
            )

    def seed_synthetic_data(self) -> Dict[str, int]:
        context = load_cx_context()
        tickets = load_tickets("customer_support")
        ticket_by_customer_issue = {(ticket.customer_id, ticket.issue_type): ticket for ticket in tickets}
        with self._write_lock, self._connect() as connection:
            connection.executemany(
                "INSERT INTO support_queues(queue, display_name, domain, approval_role) VALUES(?, ?, ?, ?) "
                "ON CONFLICT(queue) DO UPDATE SET display_name=excluded.display_name, domain=excluded.domain, approval_role=excluded.approval_role",
                _QUEUE_ROWS,
            )
            for customer in context.get("customers", []):
                connection.execute(
                    """
                    INSERT INTO customers(
                        customer_id, customer_name, plan, region, preferred_channel,
                        identity_status, crm_account_id, source_fixture
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, 'synthetic_cx_context')
                    ON CONFLICT(customer_id) DO UPDATE SET
                        customer_name=excluded.customer_name,
                        plan=excluded.plan,
                        region=excluded.region,
                        preferred_channel=excluded.preferred_channel,
                        identity_status=excluded.identity_status,
                        crm_account_id=excluded.crm_account_id
                    """,
                    (
                        customer["customer_id"],
                        customer["customer_name"],
                        customer.get("plan", "unknown"),
                        customer.get("region", "unknown"),
                        customer.get("preferred_channel", "chat"),
                        customer.get("identity_status", "unknown"),
                        customer.get("crm_account_id"),
                    ),
                )
            for case in context.get("cases", []):
                ticket = ticket_by_customer_issue.get((case.get("customer_id"), case.get("issue_type")))
                self._upsert_case(
                    connection,
                    {
                        **case,
                        "queue": _QUEUE_BY_ISSUE.get(str(case.get("issue_type")), "support_operations"),
                        "priority": getattr(ticket, "priority", "medium"),
                        "sla_deadline": getattr(ticket, "sla_deadline", None),
                        "source_fixture": "synthetic_cx_context",
                    },
                )
            for ticket in tickets:
                self._upsert_case(
                    connection,
                    {
                        "case_id": ticket.ticket_id,
                        "customer_id": ticket.customer_id,
                        "issue_type": ticket.issue_type,
                        "status": "OPEN",
                        "queue": _QUEUE_BY_ISSUE.get(ticket.issue_type, "support_operations"),
                        "priority": ticket.priority,
                        "contacted_at": ticket.created_at,
                        "sla_deadline": ticket.sla_deadline,
                        "transaction_id": None,
                        "commitment_deadline": None,
                        "commitment_met": None,
                        "source_fixture": "customer_support_tickets",
                    },
                )
            connection.executemany(
                """
                INSERT INTO accounts(
                    account_id, customer_id, product, currency, status,
                    verification_status, opened_at, source_fixture
                ) VALUES(?, ?, ?, ?, ?, ?, ?, 'synthetic_operational_seed')
                ON CONFLICT(account_id) DO UPDATE SET
                    customer_id=excluded.customer_id,
                    product=excluded.product,
                    currency=excluded.currency,
                    status=excluded.status,
                    verification_status=excluded.verification_status,
                    opened_at=excluded.opened_at
                """,
                _ACCOUNT_ROWS,
            )
            connection.executemany(
                """
                INSERT INTO transactions(
                    transaction_id, reference, customer_id, account_id, case_id,
                    transaction_type, payment_method, amount, currency, state,
                    outcome_confirmed, updated_at, source_fixture
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synthetic_operational_seed')
                ON CONFLICT(transaction_id) DO UPDATE SET
                    reference=excluded.reference,
                    customer_id=excluded.customer_id,
                    account_id=excluded.account_id,
                    case_id=excluded.case_id,
                    transaction_type=excluded.transaction_type,
                    payment_method=excluded.payment_method,
                    amount=excluded.amount,
                    currency=excluded.currency,
                    state=excluded.state,
                    outcome_confirmed=excluded.outcome_confirmed,
                    updated_at=excluded.updated_at
                """,
                _TRANSACTION_ROWS,
            )
            connection.executemany(
                """
                INSERT INTO verification_records(
                    verification_id, customer_id, account_id, case_id, status,
                    verification_type, missing_requirements, reviewed_at, source_fixture
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'synthetic_operational_seed')
                ON CONFLICT(verification_id) DO UPDATE SET
                    customer_id=excluded.customer_id,
                    account_id=excluded.account_id,
                    case_id=excluded.case_id,
                    status=excluded.status,
                    verification_type=excluded.verification_type,
                    missing_requirements=excluded.missing_requirements,
                    reviewed_at=excluded.reviewed_at
                """,
                _VERIFICATION_ROWS,
            )
            connection.executemany(
                """
                INSERT INTO approval_requests(
                    approval_id, customer_id, case_id, transaction_id, approval_type,
                    approver_role, status, requested_at, decided_at, decision_reason,
                    source_fixture
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'synthetic_operational_seed')
                ON CONFLICT(approval_id) DO UPDATE SET
                    customer_id=excluded.customer_id,
                    case_id=excluded.case_id,
                    transaction_id=excluded.transaction_id,
                    approval_type=excluded.approval_type,
                    approver_role=excluded.approver_role,
                    status=excluded.status,
                    requested_at=excluded.requested_at
                """,
                _APPROVAL_ROWS,
            )
            connection.executemany(
                """
                INSERT INTO escalations(
                    escalation_id, customer_id, case_id, approval_id, reason,
                    destination, severity, sla_minutes, status, created_at,
                    resolved_at, source_fixture
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'synthetic_operational_seed')
                ON CONFLICT(escalation_id) DO UPDATE SET
                    customer_id=excluded.customer_id,
                    case_id=excluded.case_id,
                    approval_id=excluded.approval_id,
                    reason=excluded.reason,
                    destination=excluded.destination,
                    severity=excluded.severity,
                    sla_minutes=excluded.sla_minutes,
                    status=excluded.status,
                    created_at=excluded.created_at
                """,
                _ESCALATION_ROWS,
            )
            connection.executemany(
                """
                INSERT INTO workflow_states(
                    workflow_state_id, case_id, entity_type, entity_id, state,
                    sequence, entered_at, actor, metadata_json, source_fixture
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 'synthetic_operational_seed')
                ON CONFLICT(workflow_state_id) DO UPDATE SET
                    case_id=excluded.case_id,
                    entity_type=excluded.entity_type,
                    entity_id=excluded.entity_id,
                    state=excluded.state,
                    sequence=excluded.sequence,
                    entered_at=excluded.entered_at,
                    actor=excluded.actor,
                    metadata_json=excluded.metadata_json
                """,
                [(*row[:-1], _json(row[-1])) for row in _WORKFLOW_ROWS],
            )
            for evaluation_case in load_kb_layer("eval_cases"):
                connection.execute(
                    """
                    INSERT INTO evaluation_cases(
                        evaluation_case_id, source_suite, external_benchmark, title, domain,
                        channel, language, risk_level, ticket, expected_approval_state,
                        expected_route, expected_evidence_json, unsafe_outputs_json, metrics_json
                    ) VALUES(?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(evaluation_case_id) DO UPDATE SET
                        title=excluded.title,
                        domain=excluded.domain,
                        channel=excluded.channel,
                        language=excluded.language,
                        risk_level=excluded.risk_level,
                        ticket=excluded.ticket,
                        expected_approval_state=excluded.expected_approval_state,
                        expected_route=excluded.expected_route,
                        expected_evidence_json=excluded.expected_evidence_json,
                        unsafe_outputs_json=excluded.unsafe_outputs_json,
                        metrics_json=excluded.metrics_json
                    """,
                    (
                        evaluation_case["id"],
                        SYNTHETIC_EVALUATION_SUITE,
                        evaluation_case["title"],
                        evaluation_case["domain"],
                        evaluation_case.get("channel", "unknown"),
                        evaluation_case.get("language", "en"),
                        evaluation_case.get("risk_level", "medium"),
                        evaluation_case["ticket"],
                        evaluation_case.get("expected_approval_state", "DRAFT_RECOMMENDATION"),
                        evaluation_case.get("expected_route", "support_operations"),
                        _json(evaluation_case.get("expected_evidence_ids", [])),
                        _json(evaluation_case.get("unsafe_outputs", [])),
                        _json(evaluation_case.get("metrics", [])),
                    ),
                )
        status = self.relational_status()
        return {
            "customers": status["record_counts"]["customers"],
            "cases": status["record_counts"]["cases"],
            "accounts": status["record_counts"]["accounts"],
            "transactions": status["record_counts"]["transactions"],
            "verification_records": status["record_counts"]["verification_records"],
            "approval_requests": status["record_counts"]["approval_requests"],
            "escalations": status["record_counts"]["escalations"],
            "workflow_states": status["record_counts"]["workflow_states"],
            "evaluation_cases": status["record_counts"]["evaluation_cases"],
        }

    def _upsert_case(self, connection: sqlite3.Connection, case: Mapping[str, Any]) -> None:
        connection.execute(
            """
            INSERT INTO support_cases(
                case_id, customer_id, issue_type, status, queue, priority,
                contacted_at, sla_deadline, transaction_id, commitment_deadline,
                commitment_met, source_fixture
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                customer_id=excluded.customer_id,
                issue_type=excluded.issue_type,
                status=excluded.status,
                queue=excluded.queue,
                priority=excluded.priority,
                contacted_at=excluded.contacted_at,
                sla_deadline=excluded.sla_deadline,
                transaction_id=excluded.transaction_id,
                commitment_deadline=excluded.commitment_deadline,
                commitment_met=excluded.commitment_met
            """,
            (
                case["case_id"],
                case["customer_id"],
                case["issue_type"],
                case.get("status", "OPEN"),
                case.get("queue", "support_operations"),
                case.get("priority", "medium"),
                case.get("contacted_at", "1970-01-01T00:00:00Z"),
                case.get("sla_deadline"),
                case.get("transaction_id"),
                case.get("commitment_deadline"),
                _commitment_value(case.get("commitment_met")),
                case.get("source_fixture", "synthetic"),
            ),
        )

    def list_customers(
        self,
        *,
        plan: str | None = None,
        region: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        if plan:
            filters.append("c.plan = ?")
            parameters.append(plan)
        if region:
            filters.append("c.region = ?")
            parameters.append(region)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT c.*,
                       COUNT(sc.case_id) AS total_case_count,
                       COALESCE(SUM(CASE WHEN sc.status NOT IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END), 0) AS open_case_count
                FROM customers c
                LEFT JOIN support_cases sc ON sc.customer_id = c.customer_id
                {where}
                GROUP BY c.customer_id
                ORDER BY c.customer_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def get_customer(self, customer_id: str) -> Dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT c.*,
                       COUNT(sc.case_id) AS total_case_count,
                       COALESCE(SUM(CASE WHEN sc.status NOT IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END), 0) AS open_case_count
                FROM customers c
                LEFT JOIN support_cases sc ON sc.customer_id = c.customer_id
                WHERE c.customer_id = ?
                GROUP BY c.customer_id
                """,
                (customer_id,),
            ).fetchone()
        return _row_dict(row)

    def list_cases(
        self,
        *,
        issue_type: str | None = None,
        status: str | None = None,
        queue: str | None = None,
        customer_id: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        for column, value in (
            ("sc.issue_type", issue_type),
            ("sc.status", status),
            ("sc.queue", queue),
            ("sc.customer_id", customer_id),
        ):
            if value:
                filters.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT sc.*, c.customer_name, c.plan, c.region,
                       q.display_name AS queue_name, q.approval_role
                FROM support_cases sc
                JOIN customers c ON c.customer_id = sc.customer_id
                JOIN support_queues q ON q.queue = sc.queue
                {where}
                ORDER BY sc.contacted_at DESC, sc.case_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [_row_dict(row) or {} for row in rows]

    def get_case(self, case_id: str) -> Dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT sc.*, c.customer_name, c.plan, c.region,
                       q.display_name AS queue_name, q.approval_role
                FROM support_cases sc
                JOIN customers c ON c.customer_id = sc.customer_id
                JOIN support_queues q ON q.queue = sc.queue
                WHERE sc.case_id = ?
                """,
                (case_id,),
            ).fetchone()
        return _row_dict(row)

    def list_accounts(
        self,
        *,
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        if customer_id:
            filters.append("a.customer_id = ?")
            parameters.append(customer_id)
        if status:
            filters.append("a.status = ?")
            parameters.append(status)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT a.*, c.customer_name, c.plan, c.region,
                       COUNT(t.transaction_id) AS transaction_count
                FROM accounts a
                JOIN customers c ON c.customer_id = a.customer_id
                LEFT JOIN transactions t ON t.account_id = a.account_id
                {where}
                GROUP BY a.account_id
                ORDER BY a.account_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def get_account(self, account_id: str) -> Dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT a.*, c.customer_name, c.plan, c.region,
                       COUNT(t.transaction_id) AS transaction_count
                FROM accounts a
                JOIN customers c ON c.customer_id = a.customer_id
                LEFT JOIN transactions t ON t.account_id = a.account_id
                WHERE a.account_id = ?
                GROUP BY a.account_id
                """,
                (account_id,),
            ).fetchone()
        return _row_dict(row)

    def list_transactions(
        self,
        *,
        customer_id: str | None = None,
        case_id: str | None = None,
        transaction_type: str | None = None,
        state: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        for column, value in (
            ("t.customer_id", customer_id),
            ("t.case_id", case_id),
            ("t.transaction_type", transaction_type),
            ("t.state", state),
        ):
            if value:
                filters.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT t.*, c.customer_name, a.status AS account_status,
                       sc.issue_type, sc.queue
                FROM transactions t
                JOIN customers c ON c.customer_id = t.customer_id
                JOIN accounts a ON a.account_id = t.account_id
                LEFT JOIN support_cases sc ON sc.case_id = t.case_id
                {where}
                ORDER BY t.updated_at DESC, t.transaction_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [_row_dict(row) or {} for row in rows]

    def get_transaction(self, transaction_reference: str) -> Dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT t.*, c.customer_name, a.status AS account_status,
                       sc.issue_type, sc.queue
                FROM transactions t
                JOIN customers c ON c.customer_id = t.customer_id
                JOIN accounts a ON a.account_id = t.account_id
                LEFT JOIN support_cases sc ON sc.case_id = t.case_id
                WHERE t.transaction_id = ? OR t.reference = ?
                """,
                (transaction_reference, transaction_reference),
            ).fetchone()
        return _row_dict(row)

    def list_verification_records(
        self,
        *,
        customer_id: str | None = None,
        case_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        for column, value in (("v.customer_id", customer_id), ("v.case_id", case_id), ("v.status", status)):
            if value:
                filters.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT v.*, c.customer_name, a.status AS account_status
                FROM verification_records v
                JOIN customers c ON c.customer_id = v.customer_id
                JOIN accounts a ON a.account_id = v.account_id
                {where}
                ORDER BY v.reviewed_at DESC, v.verification_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_approval_requests(
        self,
        *,
        case_id: str | None = None,
        status: str | None = None,
        approval_type: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        for column, value in (("ar.case_id", case_id), ("ar.status", status), ("ar.approval_type", approval_type)):
            if value:
                filters.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT ar.*, c.customer_name, sc.issue_type, sc.queue,
                       t.reference AS transaction_reference
                FROM approval_requests ar
                JOIN customers c ON c.customer_id = ar.customer_id
                JOIN support_cases sc ON sc.case_id = ar.case_id
                LEFT JOIN transactions t ON t.transaction_id = ar.transaction_id
                {where}
                ORDER BY ar.requested_at DESC, ar.approval_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_escalations(
        self,
        *,
        case_id: str | None = None,
        status: str | None = None,
        destination: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        for column, value in (("e.case_id", case_id), ("e.status", status), ("e.destination", destination)):
            if value:
                filters.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT e.*, c.customer_name, sc.issue_type,
                       q.display_name AS destination_name, ar.approval_type
                FROM escalations e
                JOIN customers c ON c.customer_id = e.customer_id
                JOIN support_cases sc ON sc.case_id = e.case_id
                JOIN support_queues q ON q.queue = e.destination
                LEFT JOIN approval_requests ar ON ar.approval_id = e.approval_id
                {where}
                ORDER BY e.created_at DESC, e.escalation_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_workflow_states(
        self,
        *,
        case_id: str | None = None,
        entity_type: str | None = None,
        state: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        for column, value in (("ws.case_id", case_id), ("ws.entity_type", entity_type), ("ws.state", state)):
            if value:
                filters.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT ws.*, sc.customer_id, sc.issue_type, sc.queue
                FROM workflow_states ws
                JOIN support_cases sc ON sc.case_id = ws.case_id
                {where}
                ORDER BY ws.case_id, ws.sequence
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = _decode_json(item.pop("metadata_json"), {})
            results.append(item)
        return results

    def list_evaluation_cases(
        self,
        *,
        domain: str | None = None,
        risk_level: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: List[str] = []
        parameters: List[Any] = []
        if domain:
            filters.append("domain = ?")
            parameters.append(domain)
        if risk_level:
            filters.append("risk_level = ?")
            parameters.append(risk_level)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        parameters.append(_bounded_limit(limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM evaluation_cases {where} ORDER BY evaluation_case_id LIMIT ?",
                parameters,
            ).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            for source, target in (
                ("expected_evidence_json", "expected_evidence_ids"),
                ("unsafe_outputs_json", "unsafe_outputs"),
                ("metrics_json", "metrics"),
            ):
                item[target] = _decode_json(item.pop(source), [])
            results.append(item)
        return results

    def persist_run_result(self, run_result: Mapping[str, Any] | Any) -> Dict[str, Any]:
        payload = run_result.model_dump(mode="json") if hasattr(run_result, "model_dump") else dict(run_result)
        sarvagun = payload.get("sarvagun") or {}
        customer = sarvagun.get("customer_context") or {}
        conversation = sarvagun.get("conversation") or {}
        transcript = sarvagun.get("transcript") or {}
        evaluation = payload.get("evaluation") or {}
        metrics = evaluation.get("metrics") or {}
        satisfaction = sarvagun.get("satisfaction") or {}
        quality_gate = sarvagun.get("response_quality_gate") or {}
        metadata = payload.get("metadata") or {}
        run_id = str(payload["run_id"])
        conversation_id = conversation.get("conversation_id") or metadata.get("conversation_id")
        customer_id = customer.get("customer_id")
        created_at = str(metadata.get("created_at") or transcript.get("started_at") or "1970-01-01T00:00:00Z")

        with self._write_lock, self._connect() as connection:
            if customer_id:
                connection.execute(
                    """
                    INSERT INTO customers(
                        customer_id, customer_name, plan, region, preferred_channel,
                        identity_status, crm_account_id, source_fixture
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, 'runtime')
                    ON CONFLICT(customer_id) DO UPDATE SET
                        customer_name=excluded.customer_name,
                        plan=excluded.plan,
                        region=excluded.region,
                        preferred_channel=excluded.preferred_channel,
                        identity_status=excluded.identity_status,
                        crm_account_id=COALESCE(excluded.crm_account_id, customers.crm_account_id)
                    """,
                    (
                        customer_id,
                        customer.get("customer_name", customer_id),
                        customer.get("plan", "unknown"),
                        customer.get("region", "unknown"),
                        customer.get("preferred_channel", "chat"),
                        customer.get("identity_status", "unknown"),
                        customer.get("crm_account_id"),
                    ),
                )
            if conversation_id:
                connection.execute(
                    """
                    INSERT INTO conversation_sessions(
                        conversation_id, customer_id, message_type, status, started_at, ended_at
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(conversation_id) DO UPDATE SET
                        customer_id=COALESCE(excluded.customer_id, conversation_sessions.customer_id),
                        message_type=excluded.message_type,
                        status=excluded.status,
                        ended_at=excluded.ended_at
                    """,
                    (
                        conversation_id,
                        customer_id,
                        conversation.get("message_type"),
                        "closed" if transcript.get("ended_at") else "open",
                        transcript.get("started_at", created_at),
                        transcript.get("ended_at"),
                    ),
                )
            connection.execute(
                """
                INSERT INTO agent_runs(
                    run_id, conversation_id, customer_id, execution_mode, status, resolution_stage, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    conversation_id=excluded.conversation_id,
                    customer_id=excluded.customer_id,
                    execution_mode=excluded.execution_mode,
                    status=excluded.status,
                    resolution_stage=excluded.resolution_stage
                """,
                (
                    run_id,
                    conversation_id,
                    customer_id,
                    metadata.get("execution_mode", "hybrid"),
                    payload.get("status", "completed"),
                    sarvagun.get("resolution_stage"),
                    created_at,
                ),
            )
            if conversation_id:
                for turn in transcript.get("turns", []):
                    connection.execute(
                        """
                        INSERT INTO conversation_turns(
                            turn_id, conversation_id, role, content, created_at, delivery_status
                        ) VALUES(?, ?, ?, ?, ?, ?)
                        ON CONFLICT(turn_id) DO UPDATE SET
                            content=excluded.content,
                            delivery_status=excluded.delivery_status
                        """,
                        (
                            turn["turn_id"],
                            conversation_id,
                            turn["role"],
                            turn["content"],
                            turn["created_at"],
                            turn.get("delivery_status", "recorded"),
                        ),
                    )
            connection.execute(
                """
                INSERT INTO evaluations(
                    run_id, overall_score, metrics_json, diagnosis_json, recommendations_json,
                    predicted_satisfaction, predicted_label, response_quality_score
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    overall_score=excluded.overall_score,
                    metrics_json=excluded.metrics_json,
                    diagnosis_json=excluded.diagnosis_json,
                    recommendations_json=excluded.recommendations_json,
                    predicted_satisfaction=excluded.predicted_satisfaction,
                    predicted_label=excluded.predicted_label,
                    response_quality_score=excluded.response_quality_score
                """,
                (
                    run_id,
                    float(metrics.get("overall_score", 0.0)),
                    _json(metrics),
                    _json(evaluation.get("diagnosis", [])),
                    _json(evaluation.get("recommendations", [])),
                    satisfaction.get("predicted_satisfaction"),
                    satisfaction.get("predicted_label"),
                    quality_gate.get("score"),
                ),
            )
            for tool in sarvagun.get("tool_executions", []):
                connection.execute(
                    """
                    INSERT INTO tool_executions(
                        tool_execution_id, run_id, operation, access_type, status, authorization,
                        audit_id, idempotency_key, latency_ms, simulated, result_json, error
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tool_execution_id) DO UPDATE SET
                        status=excluded.status,
                        latency_ms=excluded.latency_ms,
                        result_json=excluded.result_json,
                        error=excluded.error
                    """,
                    (
                        tool["tool_execution_id"],
                        run_id,
                        tool["operation"],
                        tool["access_type"],
                        tool["status"],
                        tool["authorization"],
                        tool["audit_id"],
                        tool["idempotency_key"],
                        int(tool.get("latency_ms", 0)),
                        1 if tool.get("simulated", True) else 0,
                        _json(tool.get("result", {})),
                        tool.get("error"),
                    ),
                )
            explicit_csat = satisfaction.get("explicit_csat")
            explicit_resolution = satisfaction.get("explicit_resolution")
            if explicit_csat is not None and explicit_resolution:
                self._record_feedback(
                    connection,
                    run_id,
                    int(explicit_csat),
                    str(explicit_resolution),
                    transcript.get("ended_at", created_at),
                )
        return {
            "backend": "sqlite",
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "persisted": True,
        }

    def record_explicit_feedback(
        self,
        run_id: str,
        explicit_csat: int,
        explicit_resolution: str,
        recorded_at: str,
    ) -> Dict[str, Any]:
        if explicit_csat < 1 or explicit_csat > 5:
            raise ValueError("explicit_csat must be between 1 and 5")
        if explicit_resolution not in {"yes", "partially", "no"}:
            raise ValueError("explicit_resolution must be yes, partially, or no")
        with self._write_lock, self._connect() as connection:
            self._record_feedback(connection, run_id, explicit_csat, explicit_resolution, recorded_at)
        return {
            "run_id": run_id,
            "explicit_csat": explicit_csat,
            "explicit_resolution": explicit_resolution,
            "recorded_at": recorded_at,
        }

    def _record_feedback(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        explicit_csat: int,
        explicit_resolution: str,
        recorded_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO explicit_feedback(run_id, explicit_csat, explicit_resolution, recorded_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                explicit_csat=excluded.explicit_csat,
                explicit_resolution=excluded.explicit_resolution,
                recorded_at=excluded.recorded_at
            """,
            (run_id, explicit_csat, explicit_resolution, recorded_at),
        )

    def relational_status(self) -> Dict[str, Any]:
        with self._connect() as connection:
            schema_row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()
            counts = {
                label: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for label, table in (
                    ("customers", "customers"),
                    ("cases", "support_cases"),
                    ("accounts", "accounts"),
                    ("transactions", "transactions"),
                    ("verification_records", "verification_records"),
                    ("approval_requests", "approval_requests"),
                    ("escalations", "escalations"),
                    ("workflow_states", "workflow_states"),
                    ("evaluation_cases", "evaluation_cases"),
                    ("conversations", "conversation_sessions"),
                    ("runs", "agent_runs"),
                    ("evaluations", "evaluations"),
                    ("tool_executions", "tool_executions"),
                    ("explicit_feedback", "explicit_feedback"),
                )
            }
            foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
            foreign_key_violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        return {
            "backend": "sqlite",
            "schema_version": schema_row[0] if schema_row else None,
            "persistent": True,
            "normalized_operational_store": True,
            "foreign_keys": foreign_keys,
            "foreign_key_violations": foreign_key_violations,
            "journal_mode": journal_mode,
            "record_counts": counts,
            "semantic_memory_store": "qdrant_or_local_vector_adapter",
            "short_term_memory_store": "redis_or_local_session_fallback",
            "evaluation_suite": SYNTHETIC_EVALUATION_SUITE,
            "external_benchmarks": {
                "tau_bench": False,
                "tau2_bench": False,
                "tau3": False,
            },
        }


def _configured_database_path() -> Path:
    configured = Path(get_settings().relational_db_path).expanduser()
    if configured.is_absolute():
        return configured
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / configured


@lru_cache(maxsize=1)
def get_relational_repository() -> RelationalRepository:
    return RelationalRepository(_configured_database_path())


def list_customers(
    *,
    plan: str | None = None,
    region: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_customers(plan=plan, region=region, limit=limit)


def get_customer(customer_id: str) -> Dict[str, Any] | None:
    return get_relational_repository().get_customer(customer_id)


def list_cases(
    *,
    issue_type: str | None = None,
    status: str | None = None,
    queue: str | None = None,
    customer_id: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_cases(
        issue_type=issue_type,
        status=status,
        queue=queue,
        customer_id=customer_id,
        limit=limit,
    )


def get_case(case_id: str) -> Dict[str, Any] | None:
    return get_relational_repository().get_case(case_id)


def list_accounts(
    *, customer_id: str | None = None, status: str | None = None, limit: int = 100
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_accounts(customer_id=customer_id, status=status, limit=limit)


def get_account(account_id: str) -> Dict[str, Any] | None:
    return get_relational_repository().get_account(account_id)


def list_transactions(
    *,
    customer_id: str | None = None,
    case_id: str | None = None,
    transaction_type: str | None = None,
    state: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_transactions(
        customer_id=customer_id,
        case_id=case_id,
        transaction_type=transaction_type,
        state=state,
        limit=limit,
    )


def get_transaction(transaction_reference: str) -> Dict[str, Any] | None:
    return get_relational_repository().get_transaction(transaction_reference)


def list_verification_records(
    *,
    customer_id: str | None = None,
    case_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_verification_records(
        customer_id=customer_id, case_id=case_id, status=status, limit=limit
    )


def list_approval_requests(
    *,
    case_id: str | None = None,
    status: str | None = None,
    approval_type: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_approval_requests(
        case_id=case_id, status=status, approval_type=approval_type, limit=limit
    )


def list_escalations(
    *,
    case_id: str | None = None,
    status: str | None = None,
    destination: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_escalations(
        case_id=case_id, status=status, destination=destination, limit=limit
    )


def list_workflow_states(
    *,
    case_id: str | None = None,
    entity_type: str | None = None,
    state: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return get_relational_repository().list_workflow_states(
        case_id=case_id, entity_type=entity_type, state=state, limit=limit
    )


def relational_status() -> Dict[str, Any]:
    return get_relational_repository().relational_status()
