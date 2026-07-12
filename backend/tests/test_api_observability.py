from fastapi.testclient import TestClient

from app.main import app


def test_health_response_includes_request_observability_headers() -> None:
    response = TestClient(app).get(
        "/health",
        headers={
            "X-Request-ID": "judge-smoke-test",
            "X-Correlation-ID": "judge-linked-flow",
        },
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "judge-smoke-test"
    assert response.headers["x-correlation-id"] == "judge-linked-flow"
    assert int(response.headers["x-response-time-ms"]) >= 0
