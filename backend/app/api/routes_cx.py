from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.cx import ConversationTurnRequest, ConversationTurnResponse, SatisfactionFeedbackRequest
from app.services.conversation import conversation_manager
from app.services.runtime import get_agent_runner
from app.services.sarvagun_lifecycle import operations_snapshot, store_explicit_feedback


router = APIRouter(tags=["sarvagun-customer-experience"])


@router.post("/conversations/turn", response_model=ConversationTurnResponse)
def process_conversation_turn(request: ConversationTurnRequest) -> ConversationTurnResponse:
    return conversation_manager.handle_turn(
        request.message,
        conversation_id=request.conversation_id,
        customer_id=request.customer_id,
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
    return {
        "record": record,
        "predicted_satisfaction": run.sarvagun.satisfaction.predicted_satisfaction,
        "explicit_csat": run.sarvagun.satisfaction.explicit_csat,
        "metrics_are_separate": True,
    }
