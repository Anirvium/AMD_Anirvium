# Anirvium AI Final Team Pitch Deck

Use this as the source deck for team alignment, demo narration, and conversion into Google Slides, PowerPoint, Canva, or PDF.

## Slide 1: Title

**Anirvium AI**  
Trajectory Intelligence for Enterprise Support Agents

**On-slide copy**

- Observe every agent step.
- Prove every decision with evidence.
- Diagnose failures.
- Improve the workflow.

**Speaker notes**

Anirvium AI is not another support chatbot. It is the control layer that makes enterprise AI support agents measurable, debuggable, and self-improving.

**Visual suggestion**

Dashboard screenshot with trajectory graph, health score, and `T-001` enterprise SLA outage visible.

---

## Slide 2: One-Sentence Mission

**Mission**  
Anirvium AI makes enterprise AI support agents observable, auditable, and continuously improvable by turning every agent decision into an evidence-backed trajectory.

**Speaker notes**

Our mission is not to replace support agents with a generic bot. Our mission is to make AI agent behavior inspectable and improvable at enterprise quality.

---

## Slide 3: The Problem

**Enterprise AI agents fail silently.**

**On-slide copy**

- Teams cannot see why an agent made a decision.
- Evidence is scattered or missing.
- Policy violations are found too late.
- SLA escalations can be missed.
- Leaders cannot measure or improve agent quality.

**Speaker notes**

Support leaders are being asked to trust AI agents in workflows involving outages, refunds, security requests, compliance questions, and high-value customers. But most systems only show the final answer or a transcript. That is not enough.

---

## Slide 4: Why The World Needs Us

**AI agents are becoming infrastructure, but agent governance is still primitive.**

**On-slide copy**

- Every enterprise wants agent automation.
- Every enterprise also needs trust, auditability, and control.
- Support workflows contain real business risk: SLA, churn, security, refunds, legal, and compliance.
- The missing layer is trajectory intelligence.

**Speaker notes**

The world needs Anirvium AI because AI agents are moving into high-stakes workflows before companies have the tools to observe and improve them.

---

## Slide 5: What Breaks If We Disappear

**Without Anirvium AI, teams go back to opaque agent behavior.**

**On-slide copy**

- Missed SLA owners.
- Unsafe refund or security commitments.
- Weak evidence grounding.
- Manual QA bottlenecks.
- No optimization loop.
- No reliable proof of why an agent acted.

**Speaker notes**

If we disappear, companies still deploy agents, but they do it blind. Failures become support escalations, customer churn, policy incidents, and internal distrust of AI.

---

## Slide 6: The Secret We Believe

**The winning enterprise AI layer is not the chatbot. It is the trajectory layer.**

**On-slide copy**

Others optimize the final response.  
We optimize the full decision path.

**Speaker notes**

Our secret is that the final response is only the surface. The enterprise value is in the path: what the agent saw, what it retrieved, which policy applied, where it escalated, what it missed, and how the workflow should change.

---

## Slide 7: Our Solution

**Anirvium AI turns every support-agent workflow into a measurable trajectory.**

**On-slide copy**

- Multi-agent workflow runner.
- Structured trajectory logger.
- Evidence and policy grounding.
- Approval-state handling.
- Deterministic evaluation engine.
- Failure diagnosis engine.
- Optimization recommendations.
- AMD-ready benchmark path.

**Speaker notes**

This is a complete observability and improvement loop. We do not just answer the customer. We measure the agent system that produced the answer.

---

## Slide 8: Product Demo Scenario

**Winning demo: high-risk enterprise support queue**

**On-slide copy**

Primary case: `T-001`  
ACME Corp has a production outage, angry sentiment, churn risk, and an SLA deadline under 60 minutes.

The support manager asks:

> Analyze today's high-priority queue, identify SLA and policy risks, draft safe responses, evaluate the trajectory, and recommend improvements.

**Speaker notes**

This scenario is easy for judges and customers to understand. It is not abstract AI governance. It is a real operational moment: a critical enterprise customer is at risk.

---

## Slide 9: How The Workflow Runs

**Seven-agent trajectory**

**On-slide copy**

1. Intake / Triage Agent
2. Knowledge Retrieval Agent
3. Policy Checker Agent
4. Escalation Agent
5. Response Drafting Agent
6. Critic / Evaluator Agent
7. Optimizer Agent

**Speaker notes**

Each agent produces structured output. Every step becomes a span with evidence IDs, tools used, latency, token estimates, confidence, risk flags, and approval state.

---

## Slide 10: What The System Produces

**Not a chatbot answer. A full operational audit trail.**

**On-slide copy**

- Final recommended actions.
- Safe customer response drafts.
- Escalation owner and route.
- Approval state.
- Evidence IDs.
- Trajectory graph.
- Trace viewer.
- Evaluation scorecard.
- Failure diagnosis.
- Workflow optimization recommendations.

**Speaker notes**

The output is useful to a support manager, an AI operations lead, and an engineering team. It tells them what to do now and how to improve the agent later.

---

## Slide 11: Evidence And Policy Grounding

**Every material claim should cite evidence.**

**On-slide copy**

Synthetic evidence examples:

- `KB-001`: outage troubleshooting workflow.
- `KB-003`: enterprise SLA escalation.
- `POL-003`: enterprise SLA policy.
- `POL-005`: evidence citation requirement.
- `KB-006`: customer communication policy.

**Speaker notes**

This is how we prevent unsupported recommendations. If an agent recommends escalation or a safe response, the system shows which KB or policy item supports that decision.

---

## Slide 12: Approval-State Safety

**Sensitive actions must stay draft-only until approved.**

**On-slide copy**

Approval states:

- `DRAFT_RECOMMENDATION`
- `APPROVAL_REQUIRED`
- `APPROVED`
- `REJECTED`
- `REVISED`
- `ESCALATED`
- `EXPIRED`

Sensitive actions:

- refunds
- compensation
- account deletion
- security escalation
- enterprise SLA escalation
- legal/compliance statements

**Speaker notes**

The system does not let sensitive workflows become final customer commitments by default. This is key for enterprise trust.

---

## Slide 13: Evaluation Engine

**We score the trajectory, not just the answer.**

**On-slide copy**

Metrics:

- task completion
- evidence grounding
- policy compliance
- hallucination risk
- escalation quality
- actionability
- missing information
- customer tone
- token efficiency
- latency efficiency
- overall score

**Speaker notes**

The first version is deterministic for demo reliability. Later we can add LLM-as-judge, but deterministic scoring gives us reproducible, inspectable behavior.

---

## Slide 14: Failure Diagnosis

**The product explains what went wrong and why it matters.**

**On-slide copy**

Each diagnosis includes:

- failure type
- severity
- affected agent
- evidence IDs
- business impact
- recommended fix
- metric impact
- confidence

**Speaker notes**

Example: `MISSING_CUSTOMER_UPDATE_CADENCE` means a critical customer response does not specify update timing. The business impact is higher churn and SLA pressure. The fix is testable.

---

## Slide 15: Optimizer Recommendations

**Anirvium AI turns failure into workflow improvement.**

**On-slide copy**

Each recommendation includes:

- target agent
- problem
- root cause
- fix
- expected metric lift
- implementation hint
- priority

**Speaker notes**

This is the self-improving part. The system does not say "make the prompt better." It says which agent to change, why, how, and what metric should move.

---

## Slide 16: Product Lifecycle

**Observe -> Evaluate -> Diagnose -> Optimize -> Verify**

**On-slide copy**

1. Run support workflow.
2. Capture trajectory spans.
3. Score trajectory quality.
4. Diagnose failure modes.
5. Recommend workflow changes.
6. Re-run benchmark.
7. Track metric lift over time.

**Speaker notes**

This is the product lifecycle. It turns agent work into an improvement loop that enterprises can operate continuously.

---

## Slide 17: Technical Architecture

**Hackathon-ready, production-shaped architecture**

**On-slide copy**

- FastAPI backend.
- React/Vite dashboard.
- Pydantic schemas.
- Synthetic local data.
- Multi-agent runner.
- Trajectory logger.
- Deterministic evaluator.
- Diagnosis and optimizer engines.
- Mock provider by default.
- OpenAI-compatible LLM provider for vLLM/ROCm.

**Speaker notes**

The stack is intentionally simple and understandable, but it is shaped like a real product. Mock mode makes demos reliable; OpenAI-compatible mode makes AMD integration straightforward.

---

## Slide 18: AMD Compute Strategy

**Prepared for AMD Developer Cloud without fake claims.**

**On-slide copy**

Current status:

Real AMD benchmark pending. Scripts and runbook are prepared. Sample files are marked as sample and are not claimed as verified AMD execution.

Prepared assets:

- `amd/run_vllm_rocm.sh`
- `amd/run_agent_benchmark.sh`
- `amd/benchmark_agent_eval.py`
- `amd/README_AMD_USAGE.md`

**Speaker notes**

We are being honest. We do not fabricate AMD throughput or screenshots. The moment GPU access is available, we can run vLLM/ROCm, benchmark the workflow, and attach real logs.

---

## Slide 19: Why We Are 10x Better Than Status Quo

**Status quo: transcript review. Anirvium AI: trajectory intelligence.**

**On-slide copy**

10x better at:

- agent auditability
- evidence tracking
- policy safety
- SLA escalation quality
- failure diagnosis
- workflow optimization
- benchmark readiness
- judge/customer comprehension

**Speaker notes**

Most tools stop at logs, transcripts, or final responses. We combine trace, evaluation, diagnosis, and optimization in one workflow.

---

## Slide 20: Dream Customer

**Enterprise support teams deploying AI agents into high-risk workflows.**

**On-slide copy**

Best buyer:

- VP of Support
- Head of AI Operations
- CX Automation Leader
- Support QA / Governance Leader

Best company types:

- B2B SaaS
- fintech
- cybersecurity
- infrastructure
- enterprise platforms

**Speaker notes**

These teams have the pain, budget, and urgency. They need AI automation, but they cannot afford opaque agent failure.

---

## Slide 21: Beachhead Market

**First market we dominate: enterprise SaaS support operations.**

**On-slide copy**

Why this niche first:

- clear SLA risk
- high customer value
- common refund/security/escalation workflows
- measurable support metrics
- synthetic demo maps directly to real buyer pain

**Speaker notes**

We should not start broad. We win one painful workflow first: enterprise SaaS support queues with AI agents.

---

## Slide 22: Moat

**Core moat: execution first, technical system second, category brand third.**

**On-slide copy**

Hard to copy because we combine:

- multi-agent trajectory capture
- evidence grounding
- policy approval states
- deterministic evaluation
- diagnosis with business impact
- optimizer with metric lift
- AMD benchmark readiness
- judge-readable product narrative

**Speaker notes**

No single feature is enough. The moat is the integrated workflow and the category: trajectory intelligence for enterprise agents.

---

## Slide 23: Where We Are Already Winning

**We already have a strong judge-readable foundation.**

**On-slide copy**

Built:

- backend APIs
- frontend dashboard
- winning demo endpoint
- synthetic enterprise data
- 7-agent workflow
- trajectory graph
- evaluation metrics
- diagnosis and optimizer
- AMD runbook and scripts
- judge-first docs
- tests

**Speaker notes**

This is no longer just an idea. The repository explains the product even without the video, which matters for automated pre-screening.

---

## Slide 24: What We Will Always Do / Never Do

**Principles**

**On-slide copy**

Always:

- make agent decisions measurable
- ground claims in evidence
- respect approval states
- diagnose root causes
- recommend testable fixes

Never:

- become just a chatbot
- use real customer data in demos
- fabricate AMD usage
- commit secrets
- make unsupported claims

**Speaker notes**

This gives the team operating boundaries. It protects credibility.

---

## Slide 25: Current Bottlenecks

**What blocks final submission quality right now**

**On-slide copy**

- Real AMD GPU benchmark still pending.
- Frontend build needs Node/npm environment.
- GitHub remote not pushed yet.
- Demo video not recorded yet.
- Slide deck PDF not exported yet.
- Hosted URL optional but not done.

**Speaker notes**

These are execution bottlenecks, not product-definition bottlenecks. The product story and core repo are in good shape.

---

## Slide 26: How We Remove Bottlenecks

**Execution plan**

**On-slide copy**

1. Get AMD Developer Cloud access.
2. Run vLLM/ROCm benchmark.
3. Attach real logs and screenshots.
4. Verify frontend with Node/npm.
5. Push GitHub repository.
6. Record 3-minute demo.
7. Export PDF deck.
8. Submit.

**Speaker notes**

This is the shortest path from strong prototype to credible hackathon submission.

---

## Slide 27: Milestones

**Submission milestones**

**On-slide copy**

Completed:

- backend mock mode
- winning demo endpoint
- dashboard workflow
- judge docs
- AMD runbook
- tests

Next:

- frontend build verification
- AMD real benchmark
- screenshots
- GitHub push
- demo video
- deck PDF
- optional hosted URL

**Speaker notes**

The team should treat the remaining work like a launch checklist.

---

## Slide 28: Metrics And Ownership

**Who owns what**

**On-slide copy**

Product quality:

- trajectory health score: engineering
- evidence grounding: AI/backend
- policy compliance: AI/backend
- escalation quality: product/AI
- UI clarity: frontend/product
- AMD proof: supervisor + engineering
- submission artifacts: supervisor + Codex

**Speaker notes**

For the hackathon, the supervisor owns access, approvals, and final submission. Codex owns implementation, docs, tests, and technical polish.

---

## Slide 29: What I Need From The Supervisor

**Human-in-the-loop asks**

**On-slide copy**

Needed:

- AMD Developer Cloud access.
- Permission to push GitHub repo.
- Node/npm capable environment.
- Final narrative approval.
- Demo video approval.
- Slide deck PDF approval.
- Decision on optional hosted URL.

**Speaker notes**

The human-in-the-loop role is essential: credentials, final judgment, recording, and submission control.

---

## Slide 30: Final Submission Target

**Before submission, we need this package complete.**

**On-slide copy**

- GitHub repo URL.
- Demo video.
- Slide deck PDF.
- AMD usage docs.
- Real AMD logs/screenshots if access arrives.
- Strong README.
- Working backend.
- Working frontend.
- Winning demo path.
- No secrets.
- Synthetic data only.

**Speaker notes**

This is the definition of done for the hackathon.

---

## Slide 31: Narrative We Want Repeated

**Memorable line**

**On-slide copy**

Anirvium AI is the trajectory intelligence layer for enterprise AI agents: it shows why agents act, whether they are safe, and how to make them better.

**Speaker notes**

Everyone on the team should be able to repeat this sentence. It is the category, the product, and the pitch.

---

## Slide 32: Why We Will Win

**Because this is not chatbot theater.**

**On-slide copy**

We win because:

- the problem is real
- the demo is concrete
- the architecture is credible
- the workflow is inspectable
- the output is operationally useful
- the optimizer creates a loop
- AMD usage is prepared honestly
- the repo is judge-readable

**Speaker notes**

Judges should immediately understand the product and why it matters. We are showing a serious enterprise AI infrastructure layer, not a toy chatbot.

---

## Appendix A: 3-Minute Pitch Script

**0:00-0:20**  
Enterprise AI support agents fail silently. Teams cannot see why they acted, whether they used evidence, or whether they violated policy.

**0:20-0:50**  
Anirvium AI analyzes a high-risk SaaS support queue. The primary ticket is ACME Corp, an enterprise outage with SLA risk under 60 minutes.

**0:50-1:30**  
The system runs triage, retrieval, policy, escalation, response drafting, critic evaluation, and optimizer recommendations.

**1:30-2:10**  
The dashboard shows the trajectory graph, trace viewer, evidence IDs, approval states, metrics, and health score.

**2:10-2:40**  
The system diagnoses failure modes and recommends concrete changes with target agent, root cause, implementation hint, and metric lift.

**2:40-3:00**  
AMD execution is pending, but the vLLM/ROCm runbook and benchmark path are prepared. Anirvium AI turns agent behavior into measurable, improvable infrastructure.

---

## Appendix B: Demo Click Path

1. Start backend.
2. Start frontend.
3. Click `Load Winning Demo`.
4. Inspect `T-001`.
5. Show final action and safe response.
6. Show trajectory graph.
7. Show trace viewer.
8. Show evaluation scorecard.
9. Show failure diagnosis.
10. Show optimizer recommendation.
11. Show AMD benchmark panel.

---

## Appendix C: Exact Backend Demo Endpoint

```bash
cd backend
uv run uvicorn app.main:app --port 8000
curl http://localhost:8000/demo/winning-run
```

Expected:

- primary ticket: `T-001`
- trajectory spans: 7
- AMD status in runbook/submission evidence: `AMD execution pending`
- score: generated by backend
- diagnosis: present
- optimization: present
