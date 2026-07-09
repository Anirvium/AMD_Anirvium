from fastapi import APIRouter

from app.services.runtime import get_agent_runner


router = APIRouter(tags=["demo"])


@router.get("/demo/winning-run")
def get_winning_demo() -> dict:
    runner = get_agent_runner()
    return runner.get_or_create_winning_demo()


@router.get("/demo/customer-support-run")
def get_customer_support_demo() -> dict:
    runner = get_agent_runner()
    return runner.get_or_create_customer_support_demo()
