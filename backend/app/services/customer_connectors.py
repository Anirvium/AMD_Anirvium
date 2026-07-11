from __future__ import annotations

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from threading import Lock
from typing import Any, Dict, List
from uuid import uuid4

from app.schemas.cx import ToolExecution
from app.services.data_loader import load_cx_context


class CustomerSystemConnector(ABC):
    @abstractmethod
    async def find_customer(self, customer_reference: str) -> Dict[str, Any] | None: ...

    @abstractmethod
    async def get_open_cases(self, customer_id: str) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def get_interaction_history(self, customer_id: str) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    async def update_case(self, case_id: str, update: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    async def add_case_note(self, case_id: str, note: str) -> Dict[str, Any]: ...

    @abstractmethod
    async def attach_transcript(self, case_id: str, transcript: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    async def create_escalation(self, case_id: str, escalation: Dict[str, Any]) -> Dict[str, Any]: ...


class MockConnector(CustomerSystemConnector):
    """Auditable synthetic connector used by the hackathon runtime.

    It exercises the same boundary a Salesforce, ticketing, Slack or internal
    CRM adapter would implement without claiming any real enterprise write.
    """

    def __init__(self) -> None:
        self.data = load_cx_context()
        self.case_updates: Dict[str, Dict[str, Any]] = {}
        self.transcripts: Dict[str, Dict[str, Any]] = {}
        self.escalations: Dict[str, Dict[str, Any]] = {}

    async def find_customer(self, customer_reference: str) -> Dict[str, Any] | None:
        return next(
            (
                dict(item)
                for item in self.data.get("customers", [])
                if item.get("customer_id") == customer_reference or item.get("crm_account_id") == customer_reference
            ),
            None,
        )

    async def get_open_cases(self, customer_id: str) -> List[Dict[str, Any]]:
        return [
            dict(item)
            for item in self.data.get("cases", [])
            if item.get("customer_id") == customer_id and item.get("status") not in {"RESOLVED", "CLOSED"}
        ]

    async def get_interaction_history(self, customer_id: str) -> List[Dict[str, Any]]:
        return [dict(item) for item in self.data.get("cases", []) if item.get("customer_id") == customer_id]

    async def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        case_id = str(case_data.get("case_id") or f"CASE-{uuid4().hex[:8].upper()}")
        created = {**case_data, "case_id": case_id, "status": case_data.get("status", "OPEN")}
        self.case_updates[case_id] = created
        return created

    async def update_case(self, case_id: str, update: Dict[str, Any]) -> Dict[str, Any]:
        before = self.case_updates.get(case_id, {"case_id": case_id})
        after = {**before, **update}
        self.case_updates[case_id] = after
        return after

    async def add_case_note(self, case_id: str, note: str) -> Dict[str, Any]:
        return {"case_id": case_id, "note_id": f"NOTE-{uuid4().hex[:8].upper()}", "note": note, "stored": True}

    async def attach_transcript(self, case_id: str, transcript: Dict[str, Any]) -> Dict[str, Any]:
        key = f"{case_id}:{transcript.get('transcript_id')}"
        self.transcripts[key] = transcript
        return {"case_id": case_id, "transcript_id": transcript.get("transcript_id"), "attached": True}

    async def create_escalation(self, case_id: str, escalation: Dict[str, Any]) -> Dict[str, Any]:
        escalation_id = str(escalation.get("escalation_id") or f"ESC-{uuid4().hex[:8].upper()}")
        created = {**escalation, "escalation_id": escalation_id, "case_id": case_id, "created": True}
        self.escalations[escalation_id] = created
        return created

    async def lookup_operational_status(self, issue_type: str) -> Dict[str, Any]:
        return dict(self.data.get("tool_results", {}).get(issue_type, {"status": "no_fixture", "outcome_confirmed": False}))


_TOOL_RESULTS: Dict[str, ToolExecution] = {}
_TOOL_LOCK = Lock()


class ToolExecutor:
    READ_OPERATIONS = {"find_customer", "get_open_cases", "get_interaction_history", "lookup_operational_status"}
    WRITE_OPERATIONS = {"create_case", "update_case", "add_case_note", "attach_transcript", "create_escalation"}

    def __init__(self, connector: MockConnector | None = None) -> None:
        self.connector = connector or MockConnector()

    def execute(
        self,
        operation: str,
        *args: Any,
        role: str = "sarvagun_support_agent",
        idempotency_key: str,
        approval_required: bool = False,
        approved: bool = True,
        before_state: Dict[str, Any] | None = None,
        timeout_ms: int = 3000,
    ) -> ToolExecution:
        if operation not in self.READ_OPERATIONS | self.WRITE_OPERATIONS:
            raise ValueError(f"Tool operation is not allowlisted: {operation}")
        with _TOOL_LOCK:
            existing = _TOOL_RESULTS.get(idempotency_key)
            if existing:
                return existing.model_copy(update={"status": "reused"})

        access_type = "read" if operation in self.READ_OPERATIONS else "write"
        execution_id = f"toolrun_{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()[:12]}"
        audit_id = f"audit_{uuid4().hex[:12]}"
        if approval_required and not approved:
            record = ToolExecution(
                tool_execution_id=execution_id,
                tool_name=f"mock_customer_system.{operation}",
                operation=operation,
                access_type=access_type,
                status="approval_required",
                authorization="authorized_but_approval_pending",
                role=role,
                idempotency_key=idempotency_key,
                timeout_ms=timeout_ms,
                approval_required=True,
                audit_id=audit_id,
                before_state=before_state or {},
            )
            with _TOOL_LOCK:
                _TOOL_RESULTS[idempotency_key] = record
            return record

        started = time.perf_counter()
        try:
            method = getattr(self.connector, operation)
            result = asyncio.run(asyncio.wait_for(method(*args), timeout=timeout_ms / 1000))
            status = "success"
            error = None
        except Exception as exc:
            result = {}
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = int((time.perf_counter() - started) * 1000)
        after_state = result if isinstance(result, dict) else {"records": result}
        record = ToolExecution(
            tool_execution_id=execution_id,
            tool_name=f"mock_customer_system.{operation}",
            operation=operation,
            access_type=access_type,
            status=status,
            authorization="mock_rbac_authorized",
            role=role,
            idempotency_key=idempotency_key,
            timeout_ms=timeout_ms,
            latency_ms=latency_ms,
            approval_required=approval_required,
            audit_id=audit_id,
            before_state=before_state or {},
            after_state=after_state,
            result=after_state,
            error=error,
            simulated=True,
        )
        with _TOOL_LOCK:
            _TOOL_RESULTS[idempotency_key] = record
        return record


mock_connector = MockConnector()
tool_executor = ToolExecutor(mock_connector)
