from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
import logging
from threading import Lock
from uuid import uuid4

from app.schemas.run import RunJobResponse, RunRequest
from app.services.agent_runner import AgentRunner


logger = logging.getLogger("uvicorn.error")


@lru_cache
def get_agent_runner() -> AgentRunner:
    return AgentRunner()


class RunJobManager:
    def __init__(self, runner: AgentRunner) -> None:
        self.runner = runner
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="anirvium-run")
        self.jobs: dict[str, RunJobResponse] = {}
        self.lock = Lock()

    def submit(self, request: RunRequest) -> RunJobResponse:
        job_id = f"job_{uuid4().hex[:12]}"
        job = RunJobResponse(
            job_id=job_id,
            status="queued",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            current_agent="Planner Agent",
            progress_message="Waiting for the AMD agent runtime",
            correlation_id=request.correlation_id,
        )
        with self.lock:
            self.jobs[job_id] = job
        logger.info(
            "run_job_queued job_id=%s correlation_id=%s tickets=%s",
            job_id,
            request.correlation_id,
            request.selected_ticket_ids or request.selection_mode,
        )
        self.executor.submit(self._execute, job_id, request)
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> RunJobResponse | None:
        with self.lock:
            job = self.jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    def _execute(self, job_id: str, request: RunRequest) -> None:
        with self.lock:
            self.jobs[job_id].status = "running"
            self.jobs[job_id].started_at = datetime.now(timezone.utc).isoformat()
            self.jobs[job_id].progress_message = "Agent workflow started"
        logger.info("run_job_started job_id=%s correlation_id=%s", job_id, request.correlation_id)
        try:
            result = self.runner.run(
                request,
                progress_callback=lambda step, total, agent, phase: self._update_progress(
                    job_id, step, total, agent, phase
                ),
            )
        except Exception as exc:
            with self.lock:
                self.jobs[job_id].status = "failed"
                self.jobs[job_id].error = f"{type(exc).__name__}: {exc}"
                self.jobs[job_id].completed_at = datetime.now(timezone.utc).isoformat()
                self.jobs[job_id].progress_message = "Agent workflow failed"
            logger.exception("run_job_failed job_id=%s correlation_id=%s", job_id, request.correlation_id)
            return
        with self.lock:
            self.jobs[job_id].status = "completed"
            self.jobs[job_id].result = result
            self.jobs[job_id].completed_at = datetime.now(timezone.utc).isoformat()
            self.jobs[job_id].current_step = self.jobs[job_id].total_steps
            self.jobs[job_id].progress_percent = 100
            self.jobs[job_id].progress_message = "Trajectory captured and evaluated"
        logger.info(
            "run_job_completed job_id=%s correlation_id=%s run_id=%s score=%s",
            job_id,
            request.correlation_id,
            result.run_id,
            result.evaluation.metrics.overall_score,
        )

    def _update_progress(self, job_id: str, step: int, total: int, agent: str, phase: str) -> None:
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                return
            job.current_step = step
            job.total_steps = total
            job.current_agent = agent
            completed_steps = step if phase == "completed" else max(0, step - 1)
            job.progress_percent = min(99, int((completed_steps / total) * 100))
            job.progress_message = f"{agent} {phase}"
        logger.info(
            "run_job_progress job_id=%s step=%s/%s agent=%s phase=%s",
            job_id,
            step,
            total,
            agent,
            phase,
        )


@lru_cache
def get_run_job_manager() -> RunJobManager:
    return RunJobManager(get_agent_runner())
