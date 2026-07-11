from __future__ import annotations

import re
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List
from uuid import uuid4

from app.schemas.cx import ConversationSignal, ConversationTurn, ConversationTurnResponse, CustomerContext
from app.services.data_loader import load_cx_context
from app.services.intent_router import resolve_customer_support_intent
from app.services.memory import add_short_term_memory


_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSION_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationManager:
    def analyze(self, message: str, *, conversation_id: str, has_support_history: bool = False) -> ConversationSignal:
        normalized = " ".join(message.lower().split())
        intent = resolve_customer_support_intent(message)

        if re.search(r"\b(goodbye|bye|that is all|that's all|nothing else|close (the )?chat)\b", normalized):
            kind = "CONVERSATION_END"
            response = "Thank you for contacting Sarvagun. I’ve kept the conversation record available for review. Goodbye."
        elif re.fullmatch(r"(hi|hello|hey|good morning|good afternoon|good evening)[!. ]*", normalized):
            kind = "GREETING"
            response = "Hello. I’m Sarvagun, Anirvium’s customer-support agent. How may I help you today?"
        elif re.search(r"\b(manager|supervisor|human agent|real person|escalate)\b", normalized):
            kind = "ESCALATION_REQUEST"
            response = None
        elif re.search(r"\b(thank you|thanks|are you there|can you help me)\b", normalized) and intent is None:
            kind = "SMALL_TALK"
            response = "I’m here and ready to help. Tell me what happened, and I’ll check the relevant case history, evidence, and support policy."
        elif re.fullmatch(r"(yes|no|okay|ok|correct|confirmed)[!. ]*", normalized):
            kind = "CONFIRMATION"
            response = "Thank you for confirming. Please share the support issue or the detail you want me to continue with."
        elif has_support_history and re.search(r"\b(same|again|still|earlier|previous|follow up|following up)\b", normalized):
            kind = "FOLLOW_UP"
            response = None
        elif re.search(r"\b(angry|frustrated|unacceptable|terrible|third contact|nobody replied|complaint)\b", normalized):
            kind = "COMPLAINT"
            response = None
        elif intent is not None or re.search(r"\b(account|payment|deposit|withdraw|bonus|kyc|verification|balance|transaction)\b", normalized):
            kind = "SUPPORT_QUERY"
            response = None
        else:
            kind = "SMALL_TALK"
            response = "I can help with payments, withdrawals, verification, account access, bonuses, and policy-sensitive support requests. What would you like me to investigate?"

        requires_run = kind in {"SUPPORT_QUERY", "FOLLOW_UP", "COMPLAINT", "ESCALATION_REQUEST"}
        return ConversationSignal(
            conversation_id=conversation_id,
            message_type=kind,
            requires_agent_run=requires_run,
            is_follow_up=kind == "FOLLOW_UP" or "again" in normalized or "third contact" in normalized,
            topic_changed=False,
            confidence=0.94 if kind != "SMALL_TALK" else 0.78,
            response=response,
        )

    def handle_turn(
        self,
        message: str,
        *,
        conversation_id: str | None = None,
        customer_id: str | None = None,
    ) -> ConversationTurnResponse:
        session_id = conversation_id or f"conv_{uuid4().hex[:12]}"
        with _SESSION_LOCK:
            session = _SESSIONS.setdefault(
                session_id,
                {
                    "conversation_id": session_id,
                    "customer_id": customer_id,
                    "started_at": _now(),
                    "turns": [],
                    "has_support_history": False,
                    "status": "open",
                },
            )
            if customer_id:
                session["customer_id"] = customer_id
            signal = self.analyze(
                message,
                conversation_id=session_id,
                has_support_history=bool(session.get("has_support_history")),
            )
            customer_turn = ConversationTurn(
                turn_id=f"turn_{uuid4().hex[:10]}",
                role="customer",
                content=message.strip(),
                created_at=_now(),
            )
            session["turns"].append(customer_turn.model_dump())
            if signal.requires_agent_run:
                session["has_support_history"] = True
            if signal.response:
                agent_turn = ConversationTurn(
                    turn_id=f"turn_{uuid4().hex[:10]}",
                    role="agent",
                    content=signal.response,
                    created_at=_now(),
                )
                session["turns"].append(agent_turn.model_dump())
            if signal.message_type == "CONVERSATION_END":
                session["status"] = "closed"
                session["closed_at"] = _now()

        add_short_term_memory(
            session_id,
            message.strip(),
            role="customer",
            metadata={"message_type": signal.message_type, "customer_id": customer_id},
        )
        if signal.response:
            add_short_term_memory(
                session_id,
                signal.response,
                role="sarvagun",
                metadata={"message_type": signal.message_type},
            )
        return ConversationTurnResponse(
            signal=signal,
            customer=self._customer_context(customer_id),
            turns=[ConversationTurn(**turn) for turn in _SESSIONS[session_id]["turns"]],
        )

    def record_agent_turn(self, conversation_id: str, content: str) -> ConversationTurn:
        turn = ConversationTurn(
            turn_id=f"turn_{uuid4().hex[:10]}",
            role="agent",
            content=content.strip(),
            created_at=_now(),
        )
        with _SESSION_LOCK:
            session = _SESSIONS.setdefault(
                conversation_id,
                {
                    "conversation_id": conversation_id,
                    "customer_id": None,
                    "started_at": _now(),
                    "turns": [],
                    "has_support_history": True,
                    "status": "open",
                },
            )
            session["turns"].append(turn.model_dump())
        add_short_term_memory(conversation_id, content.strip(), role="sarvagun")
        return turn

    def get_session(self, conversation_id: str) -> Dict[str, Any] | None:
        with _SESSION_LOCK:
            session = _SESSIONS.get(conversation_id)
            return dict(session) if session else None

    def _customer_context(self, customer_id: str | None) -> CustomerContext | None:
        if not customer_id:
            return None
        data = load_cx_context()
        customer = next((item for item in data.get("customers", []) if item["customer_id"] == customer_id), None)
        if not customer:
            return None
        cases = [item for item in data.get("cases", []) if item["customer_id"] == customer_id]
        return CustomerContext(
            **customer,
            open_case_ids=[item["case_id"] for item in cases if item.get("status") not in {"RESOLVED", "CLOSED"}],
            interaction_count=len(cases),
        )


conversation_manager = ConversationManager()
