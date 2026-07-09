from fastapi import APIRouter, HTTPException

from app.schemas.run import RunRequest, RunResult
from app.schemas.trajectory import TrajectoryResponse
from app.services.runtime import get_agent_runner


router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunResult)
def create_run(request: RunRequest) -> RunResult:
    runner = get_agent_runner()
    result = runner.run(request)
    return result


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
