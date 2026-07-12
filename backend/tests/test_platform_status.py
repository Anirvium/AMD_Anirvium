from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_platform_status_is_truthful_about_models_storage_and_benchmarks() -> None:
    response = client.get("/platform/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["systems"] == {
        "execution": "Sarvagun",
        "trajectory_intelligence": "SuperTuriya",
    }
    assert payload["models"]["embedding"]["model"] == "deterministic-token-hash-64d"
    assert payload["models"]["embedding"]["external_model_active"] is False
    assert payload["models"]["reranking"]["model"] == "deterministic-hybrid-rank-fusion"
    assert payload["storage"]["relational_operational_truth"]["backend"] == "sqlite"
    vector = payload["storage"]["semantic_vector_retrieval"]
    assert vector["terminology"] == "collections_not_clusters"
    assert set(vector["collection_roles"]) == {
        "anirvium_sarvagun_kb",
        "anirvium_superturiya_memory",
        "anirvium_superturiya_trajectories",
    }
    assert payload["external_benchmarks"]["tau3_bench"]["used"] is False
    assert payload["external_benchmarks"]["tau3_bench"]["official_score"] is None
    assert payload["production_boundaries"]["connectors"] == "simulated_and_audited"
