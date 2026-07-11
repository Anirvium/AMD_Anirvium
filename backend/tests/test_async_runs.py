import time

from fastapi.testclient import TestClient

from app.main import app


def test_async_run_returns_before_result_and_can_be_polled() -> None:
    client = TestClient(app)
    response = client.post(
        "/runs/async",
        json={
            "dataset": "customer_support",
            "selection_mode": "selected",
            "selected_ticket_ids": ["CS-001"],
        },
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    for _ in range(100):
        job = client.get(f"/runs/jobs/{job_id}")
        assert job.status_code == 200
        payload = job.json()
        if payload["status"] == "completed":
            assert payload["result"]["status"] == "completed"
            assert len(payload["result"]["trajectory"]) == 13
            return
        assert payload["status"] in {"queued", "running"}
        time.sleep(0.01)

    raise AssertionError("Async mock run did not finish")
