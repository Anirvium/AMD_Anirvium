# Judge Walkthrough

## 1. Start Backend

```bash
cd backend
uv run uvicorn app.main:app --port 8000
```

Confirm:

```bash
curl http://localhost:8000/health
```

## 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 3. Click Or Call Load Winning Demo

Frontend: click `Load Winning Demo`.

Backend:

```bash
curl http://localhost:8000/demo/winning-run
```

## 4. Inspect High-Risk Support Ticket

Focus on `T-001`: enterprise outage, ACME Corp, angry sentiment, churn risk, and SLA deadline under 60 minutes.

## 5. Inspect Trajectory Graph

The graph shows the agent path:

Triage -> retrieval -> policy -> escalation -> response -> critic -> optimizer.

## 6. Inspect Trace Viewer

Check each span for:

- agent name
- input/output summaries
- tools used
- evidence IDs
- latency
- token estimates
- confidence
- risk flags
- approval state

## 7. Inspect Evaluation Scorecard

Look for the overall trajectory health score and the metric-level breakdown.

## 8. Inspect Failure Diagnosis

Diagnosis items include:

- failure type
- severity
- affected agent
- business impact
- recommended fix
- metric impact
- confidence

## 9. Inspect Optimization Recommendations

Each recommendation includes:

- target agent
- problem
- root cause
- fix
- expected metric lift
- implementation hint
- priority

## 10. Inspect AMD Benchmark Readiness Panel

The AMD runtime evidence should say `AMD execution pending` until real AMD Developer Cloud logs and screenshots are attached. It should only say `Verified AMD run` after real evidence exists. AMD proof belongs in the runbook/submission evidence, not the primary customer-support product UI.
