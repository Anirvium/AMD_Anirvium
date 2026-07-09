# Implementation Delta Plan

## Objective

Upgrade the current Anirvium AI prototype into a judge-ready hackathon submission without fabricating AMD GPU evidence or breaking existing mock-mode functionality.

## Changes To Make

1. Judge-first documentation
   - Add `JUDGES_READ_THIS_FIRST.md`.
   - Add `docs/JUDGE_WALKTHROUGH.md`.
   - Add `docs/EVALUATION_METRICS.md`.
   - Add `docs/PRODUCT_NARRATIVE.md`.
   - Add `SUBMISSION_SUMMARY.md`.
   - Update README with a 60-second judge summary and first-inspection path.

2. Winning demo endpoint
   - Add `GET /demo/winning-run`.
   - Add `GET /runs/latest`.
   - Ensure the endpoint runs fully in mock mode with no API keys.
   - Center the demo on `T-001`, the enterprise SLA outage case.

3. Richer diagnosis and optimizer outputs
   - Extend diagnosis items with failure type, affected agent, business impact, metric impact, confidence, and recommended fix.
   - Extend optimizer recommendations with target agent, problem, root cause, fix, expected metric lift, implementation hint, and priority.
   - Preserve existing fields used by the frontend to avoid regressions.

4. Explicit approval-state handling
   - Keep sensitive actions in `APPROVAL_REQUIRED` or `ESCALATED` until approval.
   - Validate refund, security, deletion, enterprise SLA, and compensation-sensitive paths in tests.

5. Frontend judge experience
   - Add a `Load Winning Demo` button.
   - Add large judge summary cards for trajectory health, critical issues, recommended fixes, and estimated improvement.
   - Make AMD panel clearly distinguish pending evidence from verified AMD execution.
   - Improve diagnosis and optimizer display for severity and metric lift.

6. AMD readiness without false claims
   - Update AMD README with a GPU runbook and current evidence status.
   - Prepare future file paths for real AMD logs/screenshots.
   - Do not create fake real benchmark files.

7. Examples and tests
   - Add before/after agent examples.
   - Add a judge demo run example.
   - Add tests for demo endpoint, diagnosis schema, optimizer specificity, approval states, metric bounds, and trajectory observability fields.

## Validation

- Run backend tests with `cd backend && uv run pytest`.
- Frontend build will be attempted only if Node/npm are available.
- Confirm no secrets are committed.
- Confirm sample AMD assets are labeled as sample or pending.

