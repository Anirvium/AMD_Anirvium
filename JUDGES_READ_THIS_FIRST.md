# Judges Read This First

## What Anirvium AI Is

Anirvium AI has two connected products: a governed customer-support agent and a trajectory-intelligence layer. The first resolves free-form support requests. The second observes, evaluates, diagnoses, stores, and recalls the resulting execution trajectories.

## Why It Matters

Enterprise AI agents can fail silently. A support agent may miss an SLA escalation, cite weak evidence, promise a refund without approval, mishandle a security request, or produce a vague customer response. Anirvium AI gives support leaders a structured way to inspect and improve those decisions.

## Live Demo Scenario

Submit a synthetic payment or verification request. The query is resolved to the correct domain before planning; the support agent retrieves governed evidence, applies policy gates, drafts a response, and exposes the actual 13-step server-side execution progress.

The workflow shows:

- SLA risk detected.
- KB and policy evidence retrieved.
- Policy gates applied.
- Correct financial, verification, security, bonus, or priority-support owner selected.
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
curl http://localhost:8000/health/ready
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

## Trigger A Recoverable Agent Run

```bash
curl -X POST http://localhost:8000/runs/async \
  -H 'Content-Type: application/json' \
  -d '{"dataset":"customer_support","selection_mode":"selected","selected_ticket_ids":["CS-001"],"customer_query":"My account is restricted for KYC. Unblock it immediately."}'
```

Poll the returned job ID at `GET /runs/jobs/{job_id}`. The resolved case must be `CS-003`, the owner must be the Verification review queue, and answer evidence must not contain `EVAL-*` records.

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
