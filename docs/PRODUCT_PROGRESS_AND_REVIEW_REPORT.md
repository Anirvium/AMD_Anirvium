# Product Progress And Review Report

## Current Product Thesis

Anirvium AI contains **Sarvagun**, the complete governed customer-support agentic system, and **SuperTuriya**, its core trajectory-intelligence and memory loop. Sarvagun executes; SuperTuriya observes, evaluates, discovers, remembers, and improves future governed plans.

## What Has Been Built

### Sarvagun Customer-Support System

- Synthetic customer-support datasets for general enterprise support and customer-support workflow cases.
- Ticket selection by queue mode or selected ticket IDs.
- Customer query support in the frontend and backend request schema.
- Final safe draft responses with evidence IDs, approval state, confidence, compliance status, and human-escalation flags.

### Agentic Workflow

The backend executes a 13-step support-agent workflow:

1. Planner Agent
2. Attachment / Visual Evidence Agent
3. Intake / Triage Agent
4. Knowledge Retrieval Agent
5. Policy Checker Agent
6. Escalation Agent
7. Response Drafting Agent
8. Compliance Agent
9. Human Escalation Agent
10. Critic / Evaluator Agent
11. Reflection Agent
12. Learning Extraction Agent
13. Optimizer Agent

### SuperTuriya Trajectory Intelligence

- Every step emits a structured trajectory span.
- Spans include agent name, input/output summaries, evidence IDs, tool calls, latency, token estimates, confidence, risk flags, approval states, and public reasoning summaries.
- Raw hidden chain-of-thought is not shown. The UI and API expose public reasoning summaries and decision traces.
- A trajectory graph is built from spans for replay and graph discovery.

### Policy, Compliance, And Escalation

- Deterministic policy checks for sensitive support domains such as refunds, security, data deletion, compensation, SLA risk, and account-specific claims.
- Compliance agent checks final drafts against legal, regulatory, company policy, privacy, and evidence-grounding requirements.
- Human escalation agent routes low-confidence, approval-required, high-risk, or compliance-review cases into a handoff path.

### Learning And Improvement Loop

- Reflection agent reviews completed responses and identifies repeated issues.
- Learning extraction agent turns final actions, handoffs, evidence IDs, transcript-like summaries, and satisfaction signals into reusable learning artifacts.
- Optimizer agent proposes workflow fixes with target agent, root cause, implementation hint, priority, and expected metric lift.

### Memory, Vector, And Graph Layers

- Local memory layer for short-term and mid-term run summaries.
- Trajectory memory indexing hook.
- Vector backend abstraction with local mode and Qdrant-ready configuration.
- Docker Compose includes Qdrant and Redis for judge/demo environment.
- Local property graph discovery export for trajectory paths, evidence, policy checks, risks, diagnoses, and final actions.
- Neo4j is documented as an optional future production graph store; it is not required for the hackathon demo path.

### Frontend Demo UI

The frontend was rebuilt around the actual product story:

- Chat-first support workspace.
- Support ticket queue and selected-case execution.
- Live command bar with run status, run ID, selected cases, and span count.
- Agent trajectory timeline.
- Tool/action trace panel.
- Policy and guardrail panel.
- Evaluation scorecard.
- Evidence panel.
- Safe final action preview.
- Failure diagnosis panel.
- Optimizer recommendation panel.
- Replay and improvement console.

The UI auto-loads a realistic customer-support demo on page load, and the main button runs selected cases through the backend.

### AMD GPU Path

- vLLM/ROCm launch scripts.
- 48 GiB fallback strategy after the AMD notebook exposed approximately 47.98 GiB visible VRAM.
- Qwen3-8B reliable path through model alias `anirvium-text`.
- Qwen3-14B documented as stretch path.
- OpenAI-compatible LLM client integration.
- LLM-backed planner/critic path validated through AMD benchmark scripts.
- Raw model reasoning markers are sanitized from application responses.

## What Has Actually Been Proven

### Local/GitHub Product Proof

- Backend tests pass: `25 passed`.
- Frontend production build passes.
- Docker Compose path exists for frontend, backend, Redis, and Qdrant.
- API endpoints exist for health, tickets, runs, latest trajectory, evaluation, KB search, vector status, memory status, and graph discovery.

### AMD GPU Proof

The AMD notebook successfully served `anirvium-text` through vLLM/ROCm and ran the agent benchmark in LLM mode.

Key observed metrics:

- 6 tickets, 13 agent steps, 3 repeats.
- Average tokens/sec: `72.53`.
- Average trajectory score: `70.9`.
- Policy compliance: `1.0`.
- Evidence grounding: `1.0`.
- Live run produced 13 trajectory steps, 2 final actions, no raw thinking leakage, and a 78-node / 183-edge property graph.

See `amd/benchmark_results_real.md`.

## The Problem We Are Facing

The issue is not that the product has no backend, no responses, or no trajectory intelligence. The issue is deployment topology:

```text
Mac browser localhost      = Mac machine
AMD notebook localhost     = AMD remote machine
AMD vLLM localhost:8001    = AMD remote GPU server
Mac frontend localhost:5173 = local React app
```

When the local Mac frontend calls `http://localhost:8000`, it calls the Mac backend, not the AMD backend. The AMD notebook does not automatically expose its private `localhost` services to the Mac browser.

## How To Review The Product

### Review UI And Product Flow

Use the local/Docker path:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5173
```

This is the judge-safe product demo path. It is deterministic, stable, and does not require private AMD notebook access.

### Review Backend API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/demo/customer-support-run
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"dataset":"customer_support","selection_mode":"selected","selected_ticket_ids":["CS-001","CS-002"]}'
curl http://localhost:8000/runs/latest/trajectory/graph-discovery
```

### Review AMD GPU Inference

Use the AMD notebook path:

```bash
PROFILE=text_48gb bash amd/run_runtime_profile.sh
python amd/smoke_vllm_openai.py --base-url http://localhost:8001/v1 --model anirvium-text
python amd/benchmark_agent_eval.py --mode llm --dataset customer_support --tickets 6 --repeats 3
```

The AMD path proves model execution. The local/Docker path proves the frontend and product UX.

## What Is Not Fully Done

- The Mac frontend is not directly wired to the private AMD backend unless AMD port forwarding/proxy access is configured.
- The real AMD JSON benchmark logs are generated on the AMD notebook and are not committed because `amd/logs/*.json` is ignored.
- The demo does not require Neo4j; it uses local property graph discovery. Neo4j remains a future production upgrade.
- Vision/video model inference is intentionally deferred. Attachment/visual evidence is represented deterministically in the text-first path.
- The product is hackathon-demo ready, not production SaaS hardened. Authentication, tenant isolation, hosted deployment, observability vendor export, and persistent production databases remain future work.

## Readiness Assessment

Current score: `82/100`.

Strengths:

- Clear product thesis and differentiated trajectory-intelligence angle.
- Real multi-agent workflow, not just static UI.
- Structured spans, evidence IDs, approval states, policy checks, diagnosis, reflection, learning, and optimizer loop.
- Frontend is aligned to chat + workflow + observability + governance.
- AMD GPU LLM path has been validated through vLLM/ROCm benchmark runs.
- Local/Docker judge path is deterministic and runnable.

Main risks:

- Judges may expect a single hosted URL. If no hosted URL is allowed, Docker/GitHub instructions must be very clear.
- Real AMD raw logs should be copied or summarized in the repo. The summary is now added in `amd/benchmark_results_real.md`.
- If the judge tries to connect the local frontend to AMD notebook `localhost`, it will not work without port forwarding.

## Final Submission Strategy

Use two proof paths:

```text
1. GitHub/Docker path:
   Judge-facing product UI, full workflow, deterministic repeatability.

2. AMD notebook path:
   GPU-backed vLLM/Qwen proof, benchmark logs, model execution evidence.
```

This is the safest and most defensible hackathon submission model.
