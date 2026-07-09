# Trajectory Intelligence Architecture

## Product Scope

Anirvium AI is a customer-support agentic system plus a trajectory intelligence layer. The support agent handles customer requests end-to-end, while the trajectory layer observes every step, checks policy and compliance, diagnoses failures, extracts learning signals, and recommends improvements.

The product should not expose private model reasoning. It should expose auditable reasoning summaries:

- plans
- decisions
- evidence IDs
- tool calls
- policy states
- compliance status
- confidence
- human handoff state
- failure diagnosis
- improvement recommendations

## Hybrid Control Path

Anirvium uses both plan-driven and AI-driven control.

Plan-driven path:

1. Planner Agent creates an evidence contract, stop conditions, allowed tools, and policy mode.
2. Policy Checker enforces deterministic approval gates.
3. Compliance Agent checks legal, regulatory, company, privacy, and evidence rules.
4. Human Escalation Agent routes low-confidence or approval-required cases.

AI-driven path:

1. Qwen3 text model drafts, summarizes, and recommends.
2. Critic/evaluator and optimizer can optionally call the same served model.
3. Reflection and learning extraction convert completed trajectories into future improvements.

This lets the agent reason flexibly while the product remains governed by deterministic safety and approval contracts.

## 48GB Model Stack

Target:

- `Qwen/Qwen3-14B` served as `anirvium-text` in BF16 first; try FP8 only if the active ROCm/vLLM image and artifact support it cleanly.

Guaranteed path:

- `Qwen/Qwen3-8B` served as `anirvium-text`.

Emergency fallback:

- `Qwen/Qwen2.5-7B-Instruct`.

Retrieval:

- Existing local deterministic vectors and hybrid lexical retrieval.
- Add CPU embeddings such as `BAAI/bge-small-en-v1.5` or `intfloat/e5-small-v2` when dependencies are available.
- Do not spend critical GPU memory on embedding/reranker models for the 48GB demo.

Reranking:

- Skip dedicated GPU reranker for the demo.
- Use deterministic/hybrid scoring.

Policy/evaluation:

- Deterministic Python rules first.
- Same text model can provide optional critique, but deterministic metrics remain the claimable baseline.

## Graph Discovery Layer

The repo now exports each run into a local property graph:

- `Run`
- `Span`
- `AgentStep`
- `Evidence`
- `RiskFlag`
- `Tool`
- `Diagnosis`
- `FinalAction`

Edges include:

- `HAS_SPAN`
- `NEXT_STEP`
- `USES_EVIDENCE`
- `EMITS_RISK`
- `CALLS_TOOL`
- `HAS_DIAGNOSIS`
- `PRODUCES_ACTION`

API:

```text
GET /runs/latest/trajectory/graph-discovery
GET /runs/{run_id}/trajectory/graph-discovery
```

Neo4j is optional. For the hackathon demo, the local property graph is enough to prove graph-native trajectory discovery. Neo4j can be used later for advanced queries such as:

```cypher
MATCH (s:Span)-[:EMITS_RISK]->(r:RiskFlag)
RETURN s.agent_name, r.risk_flag, count(*) AS occurrences
ORDER BY occurrences DESC
```

```cypher
MATCH (s:Span)-[:USES_EVIDENCE]->(e:Evidence)
WHERE s.confidence < 0.75
RETURN s.step_id, s.agent_name, collect(e.evidence_id)
```

## Live Improvement Loop

1. Customer sends request.
2. Planner creates evidence contract and stop conditions.
3. Agent executes retrieval, policy, escalation, and response.
4. Compliance and confidence gates decide send vs human review.
5. Trajectory spans are written with reasoning summaries.
6. Property graph links spans, evidence, tools, risks, diagnosis, and actions.
7. Evaluator scores the trajectory.
8. Reflection finds repeated mistakes.
9. Learning extraction creates new KB/eval/memory artifacts.
10. Optimizer recommends changes to prompts, policy gates, retrieval, or handoff thresholds.

This is the core Anirvium thesis: support agents improve because their trajectories are observable, queryable, scored, and fed back into the system.
