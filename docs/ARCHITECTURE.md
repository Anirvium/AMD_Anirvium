# Architecture

Anirvium AI is a mock-first, AMD-ready trajectory intelligence stack for enterprise support-agent operations.

For renderable Mermaid diagrams, see [architecture_diagram.md](../architecture_diagram.md).

## Backend

The FastAPI backend exposes tickets, runs, trajectories, evaluations, and AMD benchmark metadata. `AgentRunner` coordinates the workflow and writes structured JSON runs under `backend/app/data/runs`.

Agent order:

1. Planner Agent
2. Attachment Evidence Agent
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

Each span records run ID, step ID, parent step, agent name, summaries, public reasoning summary, full output, tools, evidence IDs, latency, token estimates, model name, confidence, risk flags, approval state, and timestamp.

## Data

All demo data is synthetic:

- support tickets
- customers
- KB articles
- policies
- prior interactions
- attachment metadata

No real customer data is required or included.

## Evaluation

The default evaluator is deterministic. It measures task completion, evidence grounding, policy compliance, hallucination risk, escalation quality, actionability, missing information, customer tone, token efficiency, latency efficiency, and overall score.

The diagnosis engine maps metrics and trajectory outputs into failure categories. The reflection agent reviews repeated mistakes, the learning extraction agent converts human handoffs and transcript/satisfaction placeholders into improvement artifacts, and the optimizer converts those findings into workflow changes such as mandatory evidence checklists, approval gates, owner requirements, escalation thresholds, and token-reduction handoffs.

## Graph Discovery

The run API exports a property graph view of every trajectory:

- `GET /runs/latest/trajectory/graph-discovery`
- `GET /runs/{run_id}/trajectory/graph-discovery`

This local graph export models runs, spans, tools, evidence, risk flags, diagnosis items, and final actions. Neo4j is optional for advanced discovery; the demo does not require a live Neo4j service.

## LLM Provider

`app/services/llm_client.py` supports:

- `mock`: deterministic local mode.
- `openai_compatible`: vLLM/ROCm or any OpenAI-compatible endpoint.

Environment variables:

- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

## AMD Execution

On AMD Developer Cloud, run vLLM with ROCm using `amd/run_runtime_profile.sh`, then point the backend or benchmark script to `http://localhost:8001/v1`. Validate `text` first, then `critic`; image/video model loading is deferred. The benchmark script records throughput, latency, tokens/sec, ticket count, agent-step count, average score, and token efficiency.

## Frontend

The React dashboard is a product workspace:

- ticket queue
- chat-first support-agent run console
- final recommended actions
- trajectory timeline
- tool trace viewer
- compliance and human-handoff guardrails
- evaluation scorecards
- failure diagnosis
- optimization recommendations
