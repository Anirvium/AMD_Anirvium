from fastapi import APIRouter, HTTPException

from app.schemas.run import RunJobResponse, RunRequest, RunResult
from app.schemas.trajectory import TrajectoryResponse
from app.services.agent_runner import InvalidRunSelectionError
from app.services.graph_discovery import build_trajectory_property_graph
from app.services.runtime import get_agent_runner, get_run_job_manager


router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunResult)
def create_run(request: RunRequest) -> RunResult:
    runner = get_agent_runner()
    try:
        result = runner.run(request)
    except InvalidRunSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/runs/async", response_model=RunJobResponse, status_code=202)
def create_async_run(request: RunRequest) -> RunJobResponse:
    return get_run_job_manager().submit(request)


@router.get("/runs/jobs/{job_id}", response_model=RunJobResponse)
def get_run_job(job_id: str) -> RunJobResponse:
    job = get_run_job_manager().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Run job not found")
    return job


@router.get("/runs/latest", response_model=RunResult)
def get_latest_run() -> RunResult:
    runner = get_agent_runner()
    result = runner.get_latest_run()
    if result is None:
        raise HTTPException(status_code=404, detail="No runs have been created yet")
    return result


@router.get("/runs/latest/trajectory", response_model=TrajectoryResponse)
def get_latest_trajectory() -> TrajectoryResponse:
    runner = get_agent_runner()
    result = runner.get_latest_run()
    if result is None:
        raise HTTPException(status_code=404, detail="No runs have been created yet")
    return TrajectoryResponse(run_id=result.run_id, spans=result.trajectory, graph=result.graph)


@router.get("/runs/latest/trajectory/graph-discovery")
def get_latest_graph_discovery() -> dict:
    runner = get_agent_runner()
    result = runner.get_latest_run()
    if result is None:
        raise HTTPException(status_code=404, detail="No runs have been created yet")
    return build_trajectory_property_graph(result)


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> RunResult:
    runner = get_agent_runner()
    result = runner.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@router.get("/runs/{run_id}/trajectory", response_model=TrajectoryResponse)
def get_trajectory(run_id: str) -> TrajectoryResponse:
    runner = get_agent_runner()
    result = runner.get_trajectory(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@router.get("/runs/{run_id}/trajectory/graph-discovery")
def get_graph_discovery(run_id: str) -> dict:
    runner = get_agent_runner()
    result = runner.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return build_trajectory_property_graph(result)
