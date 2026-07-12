from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.relational_store import get_relational_repository


router = APIRouter(prefix="/data", tags=["synthetic-operational-data"])


@router.get("/status")
def get_data_status() -> dict:
    return get_relational_repository().relational_status()


@router.get("/customers")
def get_customers(
    plan: str | None = None,
    region: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    records = get_relational_repository().list_customers(plan=plan, region=region, limit=limit)
    return {"count": len(records), "synthetic_data_only": True, "records": records}


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str) -> dict:
    repository = get_relational_repository()
    customer = repository.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {
        "synthetic_data_only": True,
        "customer": customer,
        "accounts": repository.list_accounts(customer_id=customer_id),
        "cases": repository.list_cases(customer_id=customer_id, limit=500),
        "transactions": repository.list_transactions(customer_id=customer_id, limit=500),
        "verification_records": repository.list_verification_records(customer_id=customer_id, limit=500),
    }


@router.get("/cases")
def get_cases(
    issue_type: str | None = None,
    status: str | None = None,
    queue: str | None = None,
    customer_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    records = get_relational_repository().list_cases(
        issue_type=issue_type,
        status=status,
        queue=queue,
        customer_id=customer_id,
        limit=limit,
    )
    return {"count": len(records), "synthetic_data_only": True, "records": records}


@router.get("/cases/{case_id}/context")
def get_case_context(case_id: str) -> dict:
    repository = get_relational_repository()
    case = repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    customer_id = str(case["customer_id"])
    return {
        "synthetic_data_only": True,
        "case": case,
        "customer": repository.get_customer(customer_id),
        "accounts": repository.list_accounts(customer_id=customer_id, limit=500),
        "transactions": repository.list_transactions(case_id=case_id, limit=500),
        "verification_records": repository.list_verification_records(case_id=case_id, limit=500),
        "approval_requests": repository.list_approval_requests(case_id=case_id, limit=500),
        "escalations": repository.list_escalations(case_id=case_id, limit=500),
        "workflow_states": repository.list_workflow_states(case_id=case_id, limit=500),
    }


@router.get("/accounts")
def get_accounts(
    customer_id: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    records = get_relational_repository().list_accounts(customer_id=customer_id, status=status, limit=limit)
    return {"count": len(records), "synthetic_data_only": True, "records": records}


@router.get("/transactions")
def get_transactions(
    customer_id: str | None = None,
    case_id: str | None = None,
    transaction_type: str | None = None,
    state: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    records = get_relational_repository().list_transactions(
        customer_id=customer_id,
        case_id=case_id,
        transaction_type=transaction_type,
        state=state,
        limit=limit,
    )
    return {"count": len(records), "synthetic_data_only": True, "records": records}
