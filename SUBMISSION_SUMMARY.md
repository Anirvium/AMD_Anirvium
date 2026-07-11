# Submission Summary

## Project Name

Anirvium AI

## One-Sentence Mission

Anirvium AI combines Sarvagun, a governed customer-support agentic system, with SuperTuriya, the trajectory intelligence that makes every execution observable, auditable, and continuously improvable.

## Problem

Enterprise AI support agents fail silently. Teams often cannot see why an agent made a decision, whether it used evidence, whether it violated policy, or how to prevent the same failure next time.

## Solution

Sarvagun runs governed support workflows with conversation context, evidence, policy, CX signals, and audited tools. SuperTuriya observes and evaluates those trajectories, diagnoses failures, stores trusted intelligence, and applies it before future plans.

## Why Now

Companies are deploying AI agents into SLA-sensitive, refund-sensitive, and security-sensitive workflows faster than they can govern them.

## Demo Scenario

Run synthetic case `CS-002`: Priya Shah’s third unresolved withdrawal contact becomes the sixth matching unique customer, triggering deterministic recontact and incident escalation while SuperTuriya closes the trajectory-memory loop.

## Technical Architecture

- FastAPI backend.
- React/Vite dashboard.
- Stable 13-agent Sarvagun/SuperTuriya workflow.
- Governed policy, plan, autonomous, and hybrid execution modes.
- Redis operational memory and vector trajectory memory with trusted-recall controls.
- Pydantic schemas.
- Synthetic support data.
- Structured trajectory logger.
- Deterministic evaluator.
- Diagnosis and optimization engines.
- Mock and OpenAI-compatible LLM provider abstraction.
- AMD vLLM/ROCm benchmark runbook and scripts.

## AMD Usage Plan / Current Status

Current status:

```text
Real AMD/vLLM benchmark completed on AMD Developer Cloud using the 48GB text profile.
```

Verified path:

1. Start vLLM/ROCm on AMD Developer Cloud.
2. Serve `Qwen/Qwen3-8B` as `anirvium-text`.
3. Run `amd/benchmark_agent_eval.py` in `--mode llm`.
4. Save logs under `amd/logs/benchmark_llm_*.json`.
5. Use the FastAPI backend and graph-discovery endpoint for live product proof.

## What Judges Should Inspect

1. `JUDGES_READ_THIS_FIRST.md`
2. `GET /demo/winning-run`
3. Dashboard `Load Winning Demo`
4. `architecture_diagram.md`
5. `docs/EVALUATION_METRICS.md`
6. `amd/README_AMD_USAGE.md`

## Submission Artifacts Checklist

- [ ] GitHub repository URL
- [ ] Demo video
- [ ] Slide deck PDF
- [ ] AMD benchmark logs when GPU access is available
- [ ] AMD screenshots when GPU access is available
- [ ] Optional hosted URL
