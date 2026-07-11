# Three-Minute Demo Script

## 0:00-0:20 Problem

Enterprise AI support agents fail silently. They can miss SLA risk, cite weak evidence, mishandle refunds or security requests, and produce customer responses that are hard to audit.

## 0:20-0:50 Sarvagun Conversation

Open Anirvium AI. In Sarvagun, type `Hi` to show the backend conversation fast path. Then select `CS-002` and submit:

> This is my third contact. My withdrawal is processed but the bank has not received it, nobody replied to the promised update, and I am extremely frustrated.

## 0:50-1:30 Agent Workflow

Walk through the Sarvagun path:

Attachment evidence -> triage -> retrieval -> policy -> escalation -> response -> critic -> optimizer.

Explain:

- Conversation context identifies Priya Shah and two prior unresolved cases.
- Emotion analysis detects frustration and requires acknowledgement/apology.
- Recontact detection finds a missed commitment and a third contact.
- Retrieval attaches KB and policy evidence IDs.
- The audited mock status tool returns `bank_trace_under_review`.
- The sixth unique matching customer triggers one incident cluster.
- Policy, compliance, and SuperTuriya’s response gate keep the financial outcome approval-controlled.

## 1:30-2:10 SuperTuriya Trajectory Intelligence

Open SuperTuriya and show the trajectory rail, intelligence loop, and graph endpoint.

Highlight:

- agent step summaries
- evidence IDs
- tools used
- latency and token estimates
- confidence
- risk flags
- approval states
- trajectory health score
- recalled, applied, and created memory IDs
- AI-predicted satisfaction clearly separated from explicit CSAT
- transcript and audited mock connector writes

## 2:10-2:40 Failure And Optimization

Show the failure diagnosis panel and optimizer panel.

Point out at least one flaw, such as missing update cadence for a high-urgency customer response, weak evidence handling, or a policy-sensitive action that requires approval.

Then show the concrete fix:

- target agent
- root cause
- implementation hint
- expected metric lift

## 2:40-3:00 AMD And Vision

Show the runtime card and say clearly that Qwen3-8B is served through vLLM/ROCm on the AMD notebook, while connector data remains synthetic.

Close:

Sarvagun executes the support task. SuperTuriya observes, evaluates, remembers, and improves the next execution—without bypassing current policy.
