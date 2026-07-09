# Evaluation Metrics

All default scores are deterministic and run in mock mode without API keys.

## task_completion

Measures whether selected tickets receive final actions.

- Starts from `0.75`.
- Adds up to `0.25` based on the share of selected tickets with final actions.
- Failure example: a selected ticket has no recommended action.
- Good behavior: every selected ticket receives escalation, owner, response draft, evidence, and next action.

## evidence_grounding

Measures whether final actions include expected KB and policy evidence IDs.

- Starts from the ratio of used expected evidence IDs over total expected evidence IDs.
- Loses points when final actions omit required KB or policy IDs.
- Failure example: a refund recommendation lacks `POL-001` and `POL-004`.
- Good behavior: material claims cite relevant KB and policy IDs.

## policy_compliance

Measures whether sensitive tickets use the correct approval state.

- Starts from the ratio of compliant sensitive tickets over total sensitive tickets.
- Loses points when refund, security, deletion, compensation, legal, or enterprise SLA actions are not gated.
- Failure example: a data deletion request is marked final without security approval.
- Good behavior: sensitive actions remain `APPROVAL_REQUIRED` or `ESCALATED`.

## hallucination_risk

Measures customer-facing unsafe or unsupported commitments.

- Starts at `0.08`.
- Adds risk when drafts include unsafe promises such as guaranteed refunds or deletion.
- Failure example: "We will refund this today" without billing approval.
- Good behavior: response says the request is under review and cites approval requirements.

## escalation_quality

Measures whether high-risk tickets are routed to the correct owner or team.

- Starts from the ratio of correct escalations over expected escalations.
- Adds quality when enterprise outages route to engineering, refunds to billing, security requests to security, and churn risk to customer success.
- Failure example: an enterprise outage remains in generic support queue.
- Good behavior: `T-001` routes to engineering incident response plus customer success.

## actionability

Measures whether recommendations include owner, urgency, and next action.

- Starts from the share of final actions with required operational fields.
- Loses points when owner or next action is missing.
- Failure example: "Investigate issue" with no owner.
- Good behavior: "Engineering Incident Commander with success owner; verify region and send update."

## missing_information

Measures important omissions in high-urgency responses.

- Starts from the share of final actions missing expected details.
- In the overall score, lower is better.
- Failure example: a critical customer response omits next update timing.
- Good behavior: high-risk replies include owner, route, urgency, and update cadence.

## customer_tone

Measures whether responses are calm, specific, and professional.

- Starts from the share of drafts with urgency acknowledgement and clear routing language.
- Loses points when responses are vague, defensive, or generic.
- Failure example: "We are looking into it" for an angry enterprise outage.
- Good behavior: "We understand the urgency and are assigning engineering incident response."

## token_efficiency

Measures estimated token usage across spans.

- Starts at `1.0`.
- Subtracts when estimated total tokens exceed the efficiency threshold.
- Failure example: full KB body text is repeated in every agent step.
- Good behavior: retrieval emits compact evidence cards and evidence IDs.

## latency_efficiency

Measures estimated total run latency.

- Starts at `1.0`.
- Subtracts when total agent latency exceeds the efficiency threshold.
- Failure example: unnecessary redundant agent passes.
- Good behavior: each agent produces compact structured output and passes only necessary context.

## overall_score

Measures aggregate trajectory health on a 0 to 100 scale.

- Averages positive metrics.
- Inverts risk metrics: `hallucination_risk` and `missing_information`.
- Failure example: weak evidence, missed approval gates, vague responses, and high token usage.
- Good behavior: grounded, policy-safe, actionable, efficient trajectory with concrete optimizations.

