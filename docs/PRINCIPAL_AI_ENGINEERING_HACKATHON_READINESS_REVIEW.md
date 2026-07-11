# Principal AI Engineering and Hackathon Readiness Review

**Review date:** 11 July 2026  
**Scope:** Entire repository at commit `7160e6c` (`main`)  
**Review posture:** Product, AI engineering, research validity, architecture, security, operations, documentation, demo, and submission evidence

## Executive Verdict

Anirvium AI is a credible, differentiated hackathon prototype with a coherent product thesis and a working deterministic judge path. It is not yet a complete hackathon submission package and it is not production ready.

**Overall hackathon submission readiness: 68/100 — conditional go.**

- **Prototype/demo readiness: 82/100.** The backend test suite passes, the frontend production build passes, the workflow is implemented, and a curated judge flow exists.
- **AI/technical proof readiness: 71/100.** There is a real OpenAI-compatible inference path and summarized AMD benchmark evidence, but much of the product behavior remains deterministic and the raw GPU evidence is not in the repository.
- **Submission artifact readiness: 45/100.** No demo video, exported slide deck, dashboard screenshots, hosted URL, public-repository verification, or completed official checklist is present.
- **Production readiness: 35/100.** Authentication, authorization, tenant isolation, durable task state, production persistence, rate limiting, observability export, failure recovery, and security hardening are not implemented.

The correct positioning is:

> A hackathon-grade trajectory intelligence prototype with a deterministic, repeatable product demo and separately validated AMD/vLLM text inference—not a production enterprise platform and not a fully multimodal system.

## What Was Directly Verified

| Check | Result | Evidence |
| --- | --- | --- |
| Git worktree | Pass | Clean at review start; `main` aligned with `origin/main` |
| Backend tests | Pass | `25 passed in 0.42s` via `cd backend && uv run pytest -q` |
| Frontend production build | Pass | TypeScript and Vite build succeeded; 1,591 modules transformed |
| Frontend bundle | Pass with caution | Main JS 180.66 kB (55.18 kB gzip); CSS 34.52 kB (7.25 kB gzip) |
| Docker Compose syntax | Not verified | Docker is unavailable in the review environment |
| Live HTTP smoke test | Not verified | Sandbox did not permit binding a local port |
| AMD execution | Documented, not independently reproduced | Summarized metrics exist in `amd/benchmark_results_real.md`; raw logs/screenshots are absent |
| Secrets hygiene | No obvious committed secret found | `.env` ignored and `.env.example` contains blank/dummy values; this is not a formal secret scan |
| Submission media | Fail | No PDF, PNG evidence, or video artifact found; screenshot directory contains only `.gitkeep` |

## Product Review

### Strengths

1. **The product thesis is clear.** “Trajectory intelligence” is more defensible and differentiated than another support chatbot. The product connects agent decisions to evidence, policy, approval, escalation, diagnosis, and optimization.
2. **The demo scenario has enterprise stakes.** SLA breach, refund, security/deletion, churn, and escalation cases make the value legible to judges.
3. **The workflow tells a complete story.** The 13-step path covers planning, evidence, triage, retrieval, policy, escalation, response, compliance, handoff, evaluation, reflection, learning, and optimization.
4. **The UI is aligned to the product narrative.** It includes ticket selection, trajectory, traces, guardrails, evidence, evaluation, diagnosis, and recommendations instead of presenting only a chat transcript.
5. **The deterministic mode is a sensible judge fallback.** A demo that works without GPU or secrets is valuable under time-constrained judging.

### Product weaknesses

1. **The value proposition is broader than the demonstrated depth.** Observability, governance, evaluation, learning, memory, vector retrieval, graph discovery, multimodal evidence, and optimization are all claimed. Several are lightweight abstractions or deterministic demonstrations rather than deeply validated subsystems.
2. **The optimizer recommends changes but does not close the loop.** There is no controlled apply/evaluate/rollback cycle proving that a recommendation improves the next run.
3. **Human approval is represented as state, not an operational workflow.** There is no durable inbox, user identity, approve/reject action, audit actor, or resumption mechanism.
4. **The evidence experience is not truly multimodal.** Attachment cards are deterministic metadata extraction. Marketing should say “attachment-aware text-first evidence” unless real vision inference is added.
5. **No customer validation is present.** There are no interviews, design partners, usability results, task-time comparison, or baseline-vs-product study.

## AI Engineering and Research Review

### What is solid

- Typed Pydantic schemas create a consistent contract for runs, spans, tickets, and evaluations.
- The model client abstraction supports deterministic mock and OpenAI-compatible inference.
- Public reasoning summaries are used instead of exposing hidden chain-of-thought.
- Evaluation includes grounding, policy, hallucination risk, escalation, actionability, tone, token, and latency dimensions.
- Policy gates and approval states are appropriate for high-risk support actions.
- The AMD benchmark scripts record throughput, latency, ticket count, step count, score, and token efficiency.

### Research-validity limitations

1. **The evaluation is largely self-authored and deterministic.** It is useful for product telemetry but is not an independent measure of agent quality.
2. **There is no labeled benchmark report.** The repository needs a case-level table with expected decisions, observed decisions, pass/fail, error taxonomy, and aggregate confidence intervals.
3. **No baseline or ablation exists.** The submission does not show results for a plain agent versus trajectory-guided agent, or with/without policy, retrieval, critic, memory, and optimization.
4. **The benchmark mixes system and model claims.** A trajectory score of 70.9 is not meaningful without dataset definition, scorer specification, baseline, variance, and acceptance threshold.
5. **Three repeats are too few for a strong performance claim.** They are acceptable as hackathon evidence, but should be presented as observed demo measurements, not general performance.
6. **Latency is high.** The documented full benchmark averages about 190 seconds per run and 14.6 seconds per agent step. The live stage demo should use deterministic mode or a prerecorded GPU segment.
7. **The model is used selectively.** The repository should explicitly identify which agents invoke the LLM and which are deterministic. “13-agent AMD workflow” would otherwise imply more GPU execution than is implemented.

### Minimum credible evaluation package

- Freeze 20–50 synthetic cases with expected escalation, policy, evidence, and response-safety labels.
- Report precision/recall or exact-match rates for escalation and policy decisions.
- Report evidence citation accuracy and unsupported-claim rate.
- Compare: plain LLM, LLM + retrieval/policy, and full trajectory system.
- Show one failure case the system catches and one it still misses.
- Version the dataset, prompt/configuration, model, GPU/runtime, and scorer.

## Architecture and Code Quality Review

### Positive findings

- The repository has a clean frontend/backend/docs/AMD separation.
- FastAPI route boundaries and Pydantic models are easy to navigate.
- The deterministic workflow is testable and fast.
- The frontend is compact and builds without TypeScript errors.
- Generated runs and environment secrets are ignored.

### Material engineering risks

1. **Process-local run state.** `AgentRunner` keeps `runs`, `latest_run_id`, and the winning demo ID in memory. Multiple workers or restarts produce inconsistent “latest” behavior.
2. **Local JSON persistence.** This is adequate for a demo, but concurrent writes, retention, indexing, migrations, and recovery are not productionized.
3. **Synchronous long-running execution.** A multi-minute GPU run occurs inside the request path. There is no job queue, cancellation, streaming progress, retry policy, or idempotency key.
4. **Silent fallbacks.** Memory code suppresses some backend failures. A judge may believe Redis/Qdrant is active when the system has fallen back locally.
5. **Docker configuration mismatch.** Compose starts Redis and Qdrant but sets `MEMORY_BACKEND=local` and `VECTOR_BACKEND=local`. The README statement that the stack “runs ... Redis, and Qdrant” is technically true as containers, but the application does not use them by default.
6. **Configuration drift.** Default AMD metadata says `AMD Instinct MI300X 192GB`, while the captured runtime reports about 48 GiB and `gfx1100`. Hardware naming must reflect observed evidence exactly.
7. **No CI configuration found.** Local tests pass, but judges cannot see an automated clean-checkout result.
8. **No lint/type/security gates for Python.** Pytest exists, but Ruff, mypy, dependency audit, and static security checks are not configured in the project.
9. **No frontend tests.** The build passes, but there are no component, accessibility, API-error, or end-to-end tests.
10. **No API versioning or formal schema compatibility policy.** This is acceptable for the hackathon but relevant to enterprise claims.

## Security, Privacy, and Governance Review

### Good decisions

- Synthetic data is clearly stated.
- `.env` is ignored and an example file exists.
- Hidden model reasoning is sanitized from public traces.
- Sensitive actions use approval-aware states.

### Critical production gaps

- No authentication or role-based authorization.
- No tenant isolation or per-customer data boundary.
- No rate limiting, abuse prevention, request size limits, or resource quotas.
- No audit identity for approval and handoff decisions.
- Broad CORS method/header configuration; acceptable locally, not for production.
- No encryption/key-management, retention, deletion, backup, or disaster-recovery design.
- No prompt-injection or malicious attachment threat model.
- No dependency vulnerability report, SBOM, license inventory, or dataset provenance ledger.
- No PII detection/redaction pipeline beyond the synthetic-data claim.
- No formal model-risk documentation, safety test suite, or incident response procedure.

Do not describe the current system as enterprise-secure, compliant, or production-grade. Say it demonstrates governance controls and an auditable trajectory schema.

## AMD and Infrastructure Claim Review

The repository has a defensible AMD story only if the claim boundary remains precise:

- **Proven in repository documentation:** an OpenAI-compatible vLLM/ROCm endpoint was reportedly used; summarized observed metrics and commands are recorded.
- **Not independently reproducible from this checkout:** raw benchmark JSON, terminal transcript, ROCm system output, screenshots, and a machine-verifiable artifact hash.
- **Not proven:** MI300X 192GB execution, real vision inference, GPU embeddings/reranking, or a fully LLM-driven 13-step workflow.

Required fixes:

1. Commit sanitized raw AMD benchmark JSON or attach it to the submission with SHA-256 hashes.
2. Add screenshots showing `rocminfo`/device identity, vLLM startup, `/v1/models`, benchmark command, and result.
3. Replace the default MI300X label with the actual observed device, or label MI300X as a target profile rather than observed hardware.
4. State exactly which steps call Qwen and how many model calls occur per run.
5. Add a reproducibility block containing commit SHA, model revision, container/package versions, runtime flags, seed, and dataset hash.

## Hackathon Expectations and Conditions

The exact event rules are not stored in this repository, so compliance with team size, build-period originality, required partner technology, licensing, submission fields, deadlines, and prize-track conditions cannot be certified from the codebase alone.

For an AMD developer hackathon, judges are likely to reward a working prototype that connects systems/performance, models, application UX, and agentic workflows. The official AMD event description emphasizes real-world impact and building across those layers. The submission should therefore make AMD use visible and necessary—not merely a benchmark appendix.

Before submission, obtain the official event page/rulebook and create a requirement-to-evidence matrix covering:

- eligibility, geography, age, and team-size conditions;
- allowed pre-existing code and required work completed during the event;
- open-source, third-party model, dataset, and media licenses;
- mandatory AMD technology or partner-track integration;
- repository visibility and judge access;
- required written fields, architecture, demo video length/hosting, and slide format;
- deadline and timezone;
- judging rubric and prize-specific criteria;
- IP, publicity, and data-use terms;
- live judging/finalist presentation requirements.

Until that matrix is completed, rules compliance is **unknown**, not passed.

## Submission Artifact Audit

| Artifact | Status | Assessment |
| --- | --- | --- |
| Judge-first README | Present | Strong, but must remove/qualify overclaims |
| Architecture diagram | Present | Good submission asset |
| Demo script/walkthrough | Present | Good foundation |
| Working backend tests | Present | 25/25 passed locally |
| Working frontend build | Present | Passed locally |
| One-command Docker definition | Present, unverified | Must verify from a clean machine |
| Public GitHub URL/access | Unknown | Must verify in incognito/no-auth mode |
| Demo video | Missing | Submission blocker if required |
| Exported pitch deck PDF | Missing | Submission blocker if required |
| Product screenshots | Missing | High priority |
| Hosted demo URL | Missing/optional | Strongly recommended |
| Raw AMD logs | Missing from repo | High credibility risk |
| AMD screenshots | Missing | High credibility risk |
| Completed checklist | Missing | Existing checklist is entirely unchecked |
| License | Not found in reviewed file map | Add before public submission |
| CI status/badge | Missing | Recommended |
| Security/license scan | Missing | Recommended |

## Readiness Scorecard

| Area | Weight | Score | Weighted result |
| --- | ---: | ---: | ---: |
| Problem clarity and impact | 12 | 9.0/10 | 10.8 |
| Product UX and demo narrative | 14 | 8.0/10 | 11.2 |
| Technical implementation | 16 | 7.5/10 | 12.0 |
| AI/research rigor | 14 | 6.0/10 | 8.4 |
| AMD integration and proof | 14 | 6.5/10 | 9.1 |
| Reliability and reproducibility | 10 | 6.5/10 | 6.5 |
| Security and production realism | 8 | 3.5/10 | 2.8 |
| Documentation | 6 | 8.0/10 | 4.8 |
| Submission completeness | 6 | 3.5/10 | 2.1 |
| **Total** | **100** |  | **67.7/100** |

Rounded readiness: **68/100**.

## Prioritized Action Plan

### P0 — Submission blockers

1. Obtain the exact official rules/rubric and complete a compliance matrix.
2. Record a 2–3 minute demo video: problem, winning run, evidence/policy trace, caught failure, optimization, and AMD proof.
3. Export the pitch deck to PDF and verify every slide at presentation resolution.
4. Capture product and AMD evidence screenshots.
5. Verify `docker compose up --build` on a clean, non-developer machine and record the result.
6. Verify the repository is public/judge-accessible and all links work without authentication.
7. Commit or attach sanitized raw AMD evidence and correct the observed-hardware metadata.
8. Add a repository license and third-party model/dataset attribution.

### P1 — Highest score uplift

1. Add a small labeled evaluation set and baseline/ablation table.
2. Show before/after improvement on the same failed trajectory.
3. Add CI for backend tests and frontend build.
4. Make backend status responses disclose active versus fallback vector/memory backends.
5. Either configure Compose to use Redis/Qdrant or remove the implication that the app uses them.
6. Add one failure-safe UX path for backend unavailable, timeout, and malformed response.
7. Add one frontend end-to-end smoke test for the winning demo.

### P2 — Post-hackathon productization

- Durable database and asynchronous job orchestration.
- Authentication, RBAC, tenant isolation, immutable audit actors, and approval workflows.
- OpenTelemetry traces, structured logs, metrics, alerts, and SLOs.
- Prompt-injection defenses, redaction, retention controls, and security threat model.
- Real embedding/reranking evaluation and optional multimodal extraction.
- Versioned prompt/model/config registry and offline evaluation pipeline.
- Deployment manifests, backups, migrations, rollback, and disaster recovery.

## Recommended Judge Narrative

Use a five-part story:

1. **Problem:** AI support agents fail silently in policy- and SLA-sensitive work.
2. **Insight:** A transcript is insufficient; teams need an evidence-backed decision trajectory.
3. **Demo:** Run the high-risk queue, inspect evidence and policy gates, and show the safe handoff/draft.
4. **Proof:** Show deterministic reproducibility, AMD/vLLM text inference, measured latency/throughput, and one caught failure.
5. **Future:** Convert optimizer recommendations into a governed test-and-deploy improvement loop.

Avoid spending stage time listing all 13 agents. Judges care more about the problem, the decision that would otherwise go wrong, the proof that Anirvium catches it, and why AMD compute matters.

## Final Decision

**Conditional go for hackathon submission.** The product code is sufficiently complete to demonstrate, but the submission should not be sent in its current artifact state. Complete the P0 list first. If the deadline is immediate, prioritize the official-rule matrix, video, deck PDF, clean-machine Docker proof, public access, raw AMD evidence, hardware-label correction, and license.

With those items complete—and without adding major new product scope—the project can reasonably reach **82–86/100 hackathon readiness**. The largest remaining competitive improvement would then be a compact labeled evaluation plus a baseline/ablation showing that trajectory intelligence measurably prevents failures.
