from __future__ import annotations

from contextvars import ContextVar
from typing import Dict


_correlation_id: ContextVar[str | None] = ContextVar("anirvium_correlation_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("anirvium_request_id", default=None)
_run_id: ContextVar[str | None] = ContextVar("anirvium_run_id", default=None)


def bind_observability_context(
    *,
    correlation_id: str | None = None,
    request_id: str | None = None,
    run_id: str | None = None,
) -> None:
    """Bind identifiers used by request, job, agent, and model logs.

    Context variables isolate concurrent FastAPI requests. Background run
    workers bind the correlation id again when their AgentRunner starts.
    """

    if correlation_id is not None:
        _correlation_id.set(correlation_id)
    if request_id is not None:
        _request_id.set(request_id)
    if run_id is not None:
        _run_id.set(run_id)


def observability_context() -> Dict[str, str | None]:
    return {
        "correlation_id": _correlation_id.get(),
        "request_id": _request_id.get(),
        "run_id": _run_id.get(),
    }
