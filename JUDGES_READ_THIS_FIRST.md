# Judges: Read This First

## The product in one sentence

**Anirvium AI is a trajectory-intelligence control plane: Sarvagun executes governed customer-support work, and SuperTuriya makes the full decision path observable, evaluable, comparable, and safely reusable.**

## Five-minute evaluation path

Public static resilience demo: [https://anirvium.github.io/AMD_Anirvium/](https://anirvium.github.io/AMD_Anirvium/) (precomputed synthetic trajectories, no live backend). Complete reproducible product path:

1. Run `docker compose up --build` and open `http://localhost:5173`.
2. Select synthetic case `CS-002`.
3. Submit: `This is my third contact. My withdrawal is processed but the bank has not received it, nobody replied to the promised update, and I am extremely frustrated.`
4. Inspect the safe response draft, evidence IDs, tool provenance, escalation, and approval hold.
5. Open **SuperTuriya** and inspect the 13-step trace graph, trajectory health, failure signals, improvement plan, and evaluated memory loop.

Direct Docker API alternative. Agent execution is asynchronous so it survives ordinary browser/proxy request limits:

```bash
curl http://localhost:8000/health/ready
curl http://localhost:8000/platform/status
curl -X POST http://localhost:8000/runs/async \
  -H 'Content-Type: application/json' \
  -d '{"dataset":"customer_support","selection_mode":"selected","selected_ticket_ids":["CS-002"],"customer_query":"This is my third contact. My withdrawal is processed but the bank has not received it, nobody replied to the promised update, and I am extremely frustrated.","execution_mode":"hybrid"}'
```

Poll the returned `job_id` at `GET http://localhost:8000/runs/jobs/{job_id}` until `status` is `completed`.

## What the canonical scenario proves

- Sarvagun preserves the selected synthetic customer identity and linked operational context.
- It detects third-contact recontact, frustration, a missed commitment, and escalation risk.
- It retrieves reviewed policy, procedure, and response-template evidence.
- Simulated enterprise tools are fully labelled and include audit, authorization, idempotency, latency, and before/after state.
- Financial or identity-sensitive commitments remain drafts until approval.
- SuperTuriya observes nine Sarvagun execution spans and adds four intelligence spans.
- Evaluation, diagnosis, recommendation, graph discovery, and evaluated advisory memory are connected to the same run.
- Current policy always overrides recalled memory; automatic policy mutation is disabled.

## AMD use

The live path served `Qwen/Qwen3-8B` as `anirvium-text` through vLLM/ROCm on the AMD Developer Cloud allocation actually observed by the team (47.98 GiB visible VRAM, `gfx1100`). Qwen was used for customer-response drafting and routed public knowledge. Policy, guardrails, internal evaluation, deterministic embeddings, and reranking remained intentionally deterministic in the verified path.

Evidence:

- [amd/benchmark_results_real.md](amd/benchmark_results_real.md)
- [amd/README_AMD_USAGE.md](amd/README_AMD_USAGE.md)
- [amd/RUNTIME_PROFILES.md](amd/RUNTIME_PROFILES.md)

The repository does not contain the ephemeral notebook's ignored raw JSON logs. The committed human-readable result is the durable evidence artifact. No MI300X result, Fireworks use, Gemma use, or official τ score is claimed.

## Reproducibility

```bash
docker compose up --build
```

This starts frontend, backend, Redis, and Qdrant in deterministic synthetic-data mode. GitHub Actions independently runs backend tests, the frontend build, and a Docker Compose smoke test.

Current verified release checks:

- 95 backend tests pass.
- Normal and static frontend production builds pass.
- Repository is public.
- MIT license is present.
- No API credential pattern was found in tracked source.

## Submission and product source of truth

- [README.md](README.md)
- [docs/PRODUCT_0_1.md](docs/PRODUCT_0_1.md)
- [docs/FINAL_SUBMISSION_FORM.md](docs/FINAL_SUBMISSION_FORM.md)
- [docs/JUDGE_WALKTHROUGH.md](docs/JUDGE_WALKTHROUGH.md)
- [docs/SARVAGUN_SUPERTURIYA_ARCHITECTURE.md](docs/SARVAGUN_SUPERTURIYA_ARCHITECTURE.md)

## Honest boundary

This is a competition-grade, synthetic-data prototype—not a production deployment. Real CRM/payment/identity connectors, production auth and tenancy, durable distributed jobs, token streaming, managed databases, and automated policy/code deployment are future work.
