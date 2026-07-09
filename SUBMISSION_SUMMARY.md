# Submission Summary

## Project Name

Anirvium AI

## One-Sentence Mission

Anirvium AI makes enterprise AI support agents observable, auditable, and continuously improvable by turning every agent decision into an evidence-backed trajectory.

## Problem

Enterprise AI support agents fail silently. Teams often cannot see why an agent made a decision, whether it used evidence, whether it violated policy, or how to prevent the same failure next time.

## Solution

Anirvium AI runs and evaluates multi-agent support workflows with structured trajectory logging, evidence grounding, policy checks, approval states, failure diagnosis, and optimization recommendations.

## Why Now

Companies are deploying AI agents into SLA-sensitive, refund-sensitive, and security-sensitive workflows faster than they can govern them.

## Demo Scenario

Analyze a synthetic high-risk SaaS support queue centered on `T-001`, an enterprise production outage with an SLA deadline under 60 minutes and angry customer sentiment.

## Technical Architecture

- FastAPI backend.
- React/Vite dashboard.
- Deterministic seven-agent workflow.
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
