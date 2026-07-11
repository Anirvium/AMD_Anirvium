# Anirvium AI Implementation Plan

## Objective

Build a hackathon-ready Anirvium AI prototype: Sarvagun governed customer-support execution aligned with SuperTuriya trajectory intelligence, runnable with synthetic connectors and benchmarked against AMD Developer Cloud GPU-backed vLLM/ROCm inference.

## Product Story

Sarvagun handles conversations, CX context, evidence, policy, tools, escalation, and safe responses. SuperTuriya observes the stable 13-agent path, evaluates outcomes, diagnoses failures, stores trusted trajectory intelligence, and applies it before future governed plans.

## Phases

1. Backend foundation
   - FastAPI application
   - Pydantic schemas
   - Synthetic tickets, customers, KB, and policies
   - Mock-first LLM provider abstraction
   - Deterministic multi-agent runner
   - Structured trajectory logger

2. Evaluation engine
   - Deterministic scoring
   - Failure diagnosis
   - Optimization recommendations
   - Unit tests for evaluator, trajectory schema, and runner

3. Frontend dashboard
   - React/Vite/TypeScript dashboard
   - Ticket queue
   - Run console
   - Final actions
   - Trajectory graph
   - Trace viewer
   - Scorecards
   - Diagnosis and optimization panels
   - AMD benchmark panel

4. AMD artifacts
   - vLLM/ROCm launch script
   - Agent benchmark script
   - Sample benchmark output
   - AMD usage documentation and log directories

5. Submission docs
   - README
   - Architecture doc
   - Demo script
   - Slide outline
   - Submission checklist
   - Example JSON artifacts

## Definition of Done

- Backend APIs run in mock mode without secrets.
- Synthetic queue loads with at least eight realistic support tickets.
- A full multi-agent trajectory is generated end to end.
- Evaluation, diagnosis, and optimization artifacts are returned through APIs.
- Frontend dashboard renders the primary demo workflow.
- AMD folder includes reproducible commands and benchmark scripts.
- Docs explain the product clearly enough for automated pre-screening.
- Tests pass locally.
