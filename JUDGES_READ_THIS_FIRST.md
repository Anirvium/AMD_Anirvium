# Judges Read This First

## What Anirvium AI Is

Anirvium AI is a trajectory intelligence platform for enterprise support agents. It is not a chatbot. It observes, evaluates, diagnoses, and improves AI support-agent workflows by turning each decision into a trace of evidence, policy, risk, approval state, and optimization.

## Why It Matters

Enterprise AI agents can fail silently. A support agent may miss an SLA escalation, cite weak evidence, promise a refund without approval, mishandle a security request, or produce a vague customer response. Anirvium AI gives support leaders a structured way to inspect and improve those decisions.

## Demo Scenario

The winning demo analyzes a synthetic high-risk SaaS support queue. The primary case is `T-001`: ACME Corp, an enterprise customer, has a production outage with an SLA deadline under 60 minutes, angry sentiment, and churn risk.

The workflow shows:

- SLA risk detected.
- KB and policy evidence retrieved.
- Policy gates applied.
- Engineering and customer-success escalation recommended.
- Safe customer response drafted.
- Approval state used for sensitive cases.
- Trajectory evaluated.
- Failure diagnosed.
- Concrete workflow optimization recommended.

## Run Backend

Fastest containerized path:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5173
```

The Docker path runs the full dashboard, FastAPI backend, Redis, and Qdrant in deterministic synthetic-data mode.

Manual backend path:

```bash
cd backend
uv run uvicorn app.main:app --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Trigger The Winning Demo

Backend:

```bash
curl http://localhost:8000/demo/winning-run
```

Frontend:

Click `Load Winning Demo`.

## Inspect Trajectory JSON

Use:

```bash
curl http://localhost:8000/demo/winning-run
```

Or after a run:

```bash
curl http://localhost:8000/runs/latest/trajectory
```

The persisted mock run JSON is written locally under:

```text
backend/app/data/runs/
```

This directory is ignored by Git to avoid generated output churn.

## Inspect Evaluation Output

Use:

```bash
curl http://localhost:8000/demo/winning-run
curl http://localhost:8000/runs/latest/evaluation
```

The evaluation contains scorecard metrics, rich failure diagnosis, and concrete optimizer recommendations.

## AMD Usage Proof

Current status:

```text
Real AMD/vLLM benchmark completed on the observed 48GB AMD Developer Cloud runtime.
```

Evidence paths:

- `amd/benchmark_results_real.md`
- `amd/logs/benchmark_llm_20260709210044.json`
- `amd/logs/benchmark_llm_20260709212533.json`
- API proof: `/runs/latest/trajectory/graph-discovery`

See [amd/README_AMD_USAGE.md](amd/README_AMD_USAGE.md).

Note: generated JSON logs may be present only in the AMD notebook workspace because `amd/logs/*.json` is ignored to avoid committing generated output churn. The verified metrics are summarized in [amd/benchmark_results_real.md](amd/benchmark_results_real.md).
