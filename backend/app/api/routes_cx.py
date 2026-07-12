from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from app.schemas.cx import ConversationTurnRequest, ConversationTurnResponse, SatisfactionFeedbackRequest
from app.services.capability_router import capability_router
from app.services.conversation import conversation_manager
from app.services.relational_store import get_relational_repository
from app.services.runtime import get_agent_runner
from app.services.sarvagun_lifecycle import operations_snapshot, store_explicit_feedback


router = APIRouter(tags=["sarvagun-customer-experience"])
logger = logging.getLogger("uvicorn.error")


@router.post("/conversations/turn", response_model=ConversationTurnResponse)
def process_conversation_turn(payload: ConversationTurnRequest, request: Request) -> ConversationTurnResponse:
    conversation_id = payload.conversation_id or f"conv_{uuid4().hex[:12]}"
    session = conversation_manager.get_session(conversation_id)
    if (
        session
        and payload.customer_id
        and session.get("customer_id")
        and session["customer_id"] != payload.customer_id
    ):
        raise HTTPException(
            status_code=409,
            detail="A conversation cannot switch customer identity; start a new conversation.",
        )
    signal = conversation_manager.analyze(
        payload.message,
        conversation_id=conversation_id,
        has_support_history=bool(session and session.get("has_support_history")),
    )
    route = capability_router.route(
        payload.message,
        conversation_kind=signal.message_type,
        conversation_requires_agent=signal.requires_agent_run,
    )
    direct_result = capability_router.execute(route, payload.message)
    logger.info(
        "capability_routed correlation_id=%s conversation_id=%s route_id=%s capability=%s execution_path=%s requires_agent=%s result_status=%s",
        request.state.correlation_id,
        conversation_id,
        route.route_id,
        route.capability,
        route.execution_path,
        route.requires_agent_run,
        direct_result.status if direct_result else "pending_agent_execution",
    )
    if direct_result is not None:
        signal = signal.model_copy(
            update={
                "requires_agent_run": False,
                "response": direct_result.answer,
                "confidence": route.confidence,
            }
        )
    elif route.requires_agent_run:
        signal = signal.model_copy(update={"requires_agent_run": True, "response": None, "confidence": route.confidence})
    return conversation_manager.handle_turn(
        payload.message,
        conversation_id=conversation_id,
        customer_id=payload.customer_id,
        signal_override=signal,
        capability_route=route,
        direct_result=direct_result,
    )


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    session = conversation_manager.get_session(conversation_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return session


@router.get("/cx/operations")
def get_cx_operations() -> dict:
    return operations_snapshot()


@router.get("/cx/transcripts/{run_id}")
def get_transcript(run_id: str) -> dict:
    run = get_agent_runner().get_run(run_id)
    if run is None or run.sarvagun is None:
        raise HTTPException(status_code=404, detail="Sarvagun transcript not found")
    return run.sarvagun.transcript.model_dump(mode="json")


@router.post("/cx/feedback")
def record_feedback(request: SatisfactionFeedbackRequest) -> dict:
    runner = get_agent_runner()
    run = runner.get_run(request.run_id)
    if run is None or run.sarvagun is None:
        raise HTTPException(status_code=404, detail="Sarvagun run not found")
    run.sarvagun.satisfaction.explicit_csat = request.explicit_csat
    run.sarvagun.satisfaction.explicit_resolution = request.explicit_resolution
    runner.logger.save_run(run.run_id, run.model_dump(mode="json"))
    record = store_explicit_feedback(request.run_id, request.explicit_csat, request.explicit_resolution)
    try:
        repository = get_relational_repository()
        repository.persist_run_result(run)
        relational_persistence = repository.record_explicit_feedback(
            request.run_id,
            request.explicit_csat,
            request.explicit_resolution,
            record["recorded_at"],
        )
        relational_persistence["persisted"] = True
    except Exception as exc:
        relational_persistence = {
            "backend": "sqlite",
            "persisted": False,
            "error": type(exc).__name__,
        }
    return {
        "record": record,
        "relational_persistence": relational_persistence,
        "predicted_satisfaction": run.sarvagun.satisfaction.predicted_satisfaction,
        "explicit_csat": run.sarvagun.satisfaction.explicit_csat,
        "metrics_are_separate": True,
    }
