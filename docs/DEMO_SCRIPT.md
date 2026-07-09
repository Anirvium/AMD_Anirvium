# Three-Minute Demo Script

## 0:00-0:20 Problem

Enterprise AI support agents fail silently. They can miss SLA risk, cite weak evidence, mishandle refunds or security requests, and produce customer responses that are hard to audit.

## 0:20-0:50 Demo Input

Open Anirvium AI and load the high-risk SaaS support queue. Focus on `T-001`: ACME Corp, an enterprise customer, has a production outage, an SLA deadline under 60 minutes, angry sentiment, and churn risk.

Click `Load Winning Demo`.

## 0:50-1:30 Agent Workflow

Walk through the multi-agent path:

Attachment evidence -> triage -> retrieval -> policy -> escalation -> response -> critic -> optimizer.

Explain:

- Attachment evidence extracts metadata-driven findings and `VIS-*` evidence IDs without loading an image/video model in the text-first path.
- Triage detects SLA and sentiment risk.
- Retrieval attaches KB and policy evidence IDs.
- Policy checker gates sensitive actions.
- Escalation assigns route, owner, urgency, and next action.
- Response drafter creates safe customer responses.
- Critic scores the trajectory.
- Optimizer recommends concrete workflow changes.

## 1:30-2:10 Trajectory Intelligence

Show the trajectory graph and trace viewer.

Highlight:

- agent step summaries
- evidence IDs
- tools used
- latency and token estimates
- confidence
- risk flags
- approval states
- trajectory health score

## 2:10-2:40 Failure And Optimization

Show the failure diagnosis panel and optimizer panel.

Point out at least one flaw, such as missing update cadence for a high-urgency customer response, weak evidence handling, or a policy-sensitive action that requires approval.

Then show the concrete fix:

- target agent
- root cause
- implementation hint
- expected metric lift

## 2:40-3:00 AMD And Vision

Show the AMD benchmark panel. Say clearly:

Real AMD benchmark is pending. The vLLM/ROCm runbook and benchmark scripts are ready, and real logs/screenshots will be attached after AMD Developer Cloud GPU access is available.

Close:

Anirvium AI makes enterprise AI agents measurable, debuggable, and self-improving by turning every decision into a trajectory of evidence, reasoning, risk, and optimization.
