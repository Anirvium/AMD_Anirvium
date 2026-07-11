from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from threading import Lock
from uuid import uuid4

from app.schemas.run import RunJobResponse, RunRequest
from app.services.agent_runner import AgentRunner


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
        )
        with self.lock:
            self.jobs[job_id] = job
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
        try:
            result = self.runner.run(request)
        except Exception as exc:
            with self.lock:
                self.jobs[job_id].status = "failed"
                self.jobs[job_id].error = f"{type(exc).__name__}: {exc}"
                self.jobs[job_id].completed_at = datetime.now(timezone.utc).isoformat()
            return
        with self.lock:
            self.jobs[job_id].status = "completed"
            self.jobs[job_id].result = result
            self.jobs[job_id].completed_at = datetime.now(timezone.utc).isoformat()


@lru_cache
def get_run_job_manager() -> RunJobManager:
    return RunJobManager(get_agent_runner())
