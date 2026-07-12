# Judge Walkthrough

## Before you start

Use the public repository at `https://github.com/Anirvium/AMD_Anirvium`. The default Docker path uses synthetic data and deterministic model mode so the entire product remains reproducible without private AMD credentials.

## 1. Start the complete stack

```bash
docker compose up --build
```

Wait for the frontend and backend, then verify:

```bash
curl http://localhost:5173/api/health
curl http://localhost:8000/health/ready
```

Open `http://localhost:5173`.

## 2. Prove the typed router

In the Sarvagun composer, try:

1. `List all customers`
2. `Show all payment-failure cases`
3. `Open CS-001`

These prompts use exact read-only synthetic operational records. They do not unnecessarily execute thirteen agents.

## 3. Run the canonical governed workflow

Select `CS-002` and submit:

> This is my third contact. My withdrawal is processed but the bank has not received it, nobody replied to the promised update, and I am extremely frustrated.

The frontend creates a recoverable asynchronous job and polls server-side progress. The rail shows each current agent and final structured span.

## 4. Inspect Sarvagun

Verify:

- customer identity and case stay linked;
- recontact and frustration are detected;
- governed KB evidence IDs are visible;
- payment/case connector executions are labelled simulated;
- evidence, authorization, idempotency, before/after state, and audit IDs are recorded;
- the draft does not promise an unapproved financial outcome;
- the final disposition is held for human review when required.

## 5. Inspect SuperTuriya

Open the **SuperTuriya** tab and inspect:

- trajectory health and metric cards;
- the discovered Sarvagun → SuperTuriya trace graph;
- selected-node tools, evidence, latency, confidence, and risk;
- failure signals and affected agents;
- concrete improvement recommendations;
- recalled, applied, and created memory IDs;
- explicit `automatic_policy_mutation=false` safety state.

## 6. Inspect the API evidence

The following URLs are the direct Docker backend path:

```bash
curl http://localhost:8000/runs/latest
curl http://localhost:8000/runs/latest/trajectory
curl http://localhost:8000/runs/latest/evaluation
curl http://localhost:8000/runs/latest/trajectory/graph-discovery
curl http://localhost:8000/platform/status
curl http://localhost:8000/data/cases/CS-002/context
```

For a currently authorized AMD notebook session, use the same routes through `https://radeon-global.anruicloud.com/spaces/<instance-id>/8501/api/...`; the VM-internal direct backend remains `http://127.0.0.1:8000`.

Compare two persisted runs with:

```text
GET /runs/compare?baseline_run_id=...&candidate_run_id=...
```

## 7. Understand AMD's role

The committed AMD result summary proves the text-generation path ran through Qwen3-8B served by vLLM/ROCm on the observed AMD Developer Cloud GPU. The live model drafts responses and answers routed public-knowledge queries; safety-critical policy, approval, compliance, and the default evaluator remain deterministic.

Read:

- `amd/benchmark_results_real.md`
- `amd/README_AMD_USAGE.md`
- `amd/RUNTIME_PROFILES.md`

Do not interpret the internal score as a Track 3 benchmark or official τ result.

## 8. Review the honest boundary

The current system is a synthetic-data prototype. It does not claim live Salesforce, payment, identity, Slack, or Citrix integration; production auth/tenancy; distributed durable jobs; token streaming; automatic policy mutation; or a stable private AMD notebook after the event allocation ends.
