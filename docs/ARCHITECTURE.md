# Architecture

Anirvium AI is a mock-first, AMD-ready trajectory intelligence stack for enterprise support-agent operations.

For renderable Mermaid diagrams, see [architecture_diagram.md](../architecture_diagram.md).

## Backend

The FastAPI backend exposes tickets, runs, trajectories, evaluations, and AMD benchmark metadata. `AgentRunner` coordinates the workflow and writes structured JSON runs under `backend/app/data/runs`.

Agent order:

1. Attachment Evidence Agent
2. Intake / Triage Agent
3. Knowledge Retrieval Agent
4. Policy Checker Agent
5. Escalation Agent
6. Response Drafting Agent
7. Compliance Agent
8. Human Escalation Agent
9. Critic / Evaluator Agent
10. Reflection Agent
11. Learning Extraction Agent
12. Optimizer Agent

Each span records run ID, step ID, parent step, agent name, summaries, full output, tools, evidence IDs, latency, token estimates, model name, confidence, risk flags, approval state, and timestamp.

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
