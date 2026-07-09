# Frontend Demo Readiness Review

## Principal Assessment

The frontend is now a three-column customer-support agent cockpit with trajectory intelligence running beside it. It presents Anirvium AI as an end-to-end support agentic system, not a generic observability dashboard.

Current frontend readiness score: 91/100.

The remaining 10 points depend on live AMD inference screenshots, Qdrant/Redis status in the remote notebook, and one final visual pass on the exact projector/browser viewport used for judging.

## What Was Strong Before

- The product already had real backend data: tickets, spans, graph nodes, evidence cards, final actions, evaluation metrics, failure diagnosis, and optimizer recommendations.
- Components were cleanly separated and easy to reuse.
- The dashboard already had the right conceptual pieces: queue, run console, graph, trace viewer, evidence, eval, diagnosis, optimizer, KB readiness, and AMD readiness.
- The API types were explicit enough to build derived observability panels without backend churn.

## Weak Areas Fixed

- The UI felt like a useful internal admin dashboard, not a premium agent infrastructure product.
- The main screen did not immediately show the actual customer-support agent experience.
- Policy, auditability, tool/action trace, and executive summary were implicit rather than visible.
- The flow mixed panels without a clear demo story.
- The styling was light, flat, and less differentiated than the strength of the backend architecture.
- The AMD benchmark panel distracted from the product story and was removed from the main demo surface.

## Judge-Facing Panels Now Present

1. Top KPI strip for resolution quality, unsafe action blocks, escalation rate, handling time, and customer tone.
2. Left column: customer support chat/query workspace, matched case, and safe response preview.
3. Center column: live trajectory timeline plus tool/action trace.
4. Right column: trajectory intelligence with policy gates, evaluation/confidence, and evidence citations.
5. Resolution band: final safe support answer backed by citations.
6. Bottom replay drawer: raw spans, observations, diagnosis, optimizer recommendations, and support queue.

## Final Demo Flow

1. Open the dashboard and start at the customer query box in the left column.
2. Enter or select a realistic customer support request.
3. Click "Run Support Agent".
4. Show the matched support case and safe response preview.
5. Move to the center column and show the trajectory timeline plus tool/action trace.
6. Move to the right column and show policy gates, confidence/eval score, and evidence citations.
7. Show the resolution band with the final safe answer.
8. Open the bottom replay drawer to show raw spans, diagnosis, and optimizer recommendations.
9. Mention AMD runtime only as the deployment path, not as the main product UI.

## Observability Stack Decision

Chosen for the hackathon build:

- Custom trajectory logger and span schema as the primary demo trace store.
- JSON-backed run artifacts for reproducible local and notebook demos.
- Frontend-derived observability views over spans, tools, policy states, evidence IDs, and audit events.
- Qdrant-backed trajectory memory for long-term trajectory intelligence.

Deferred integrations:

- OpenTelemetry export for standard traces.
- Arize Phoenix for AI tracing/evaluation UI after the custom trace schema is stable.
- Langfuse for LLM prompt/model observability after live inference is proven.
- Helicone only if we need an LLM gateway/proxy, which is not core for the MI300X local vLLM path.

Rationale:

The current product already has domain-specific spans that include agent name, approval state, evidence IDs, risk flags, token counts, latency, model name, and full output. A generic tracing tool would not automatically understand the support-policy semantics that make Anirvium compelling. For the hackathon, the strongest demo is the support agent workspace plus trajectory intelligence running beside it, with OpenTelemetry-compatible export as the production bridge.

## Immediate Remaining Frontend Items

- Capture screenshots after running the chat-first support flow with live backend data.
- Verify the support workspace at the exact demo viewport.
- Keep generated `frontend/dist/` ignored.
- Do not add public raw datasets to the frontend bundle.
- After AMD inference, keep benchmark proof in docs or a secondary route, not the main product flow.
