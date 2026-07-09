# Knowledge Architecture For Anirvium AI

## Goal

Anirvium should turn messy customer-support knowledge into an evaluation-driven agent control plane:

```text
source documents
-> anonymized source KB
-> structured articles
-> policy records
-> procedures
-> templates
-> eval cases
-> retrieval + policy gate + trajectory scoring
```

## Why Structure Matters

The source corpus mixes several knowledge types:

- public-style customer answers
- internal-only operating procedures
- escalation paths
- KYC/AML verification rules
- payment task rules
- screenshots/video references
- tool instructions
- response templates
- bilingual call/chat snippets
- priority-customer handling examples
- security/confidentiality constraints

If all of this goes straight into vector search, the agent may retrieve internal-only instructions and expose them to customers. The product needs explicit separation between knowledge, policy, procedure, and customer-facing response.

The 12 newly ingested support documents make this separation more important. Most of the new material is template-heavy; it is excellent for response style, eval seeds, and edge-case discovery, but it should not be treated as policy until reviewed.

## Recommended Data Model

### Knowledge Article

```json
{
  "article_id": "KB-VERIFY-001",
  "title": "Voluntary account verification",
  "domain": "verification",
  "audience": "customer_safe",
  "summary": "...",
  "body": "...",
  "source_refs": ["source_material/customer_support_operations_anonymized.md"],
  "tags": ["kyc", "verification", "identity"],
  "effective_status": "draft"
}
```

### Policy Rule

```json
{
  "policy_id": "POL-VERIFY-001",
  "domain": "verification",
  "trigger": "customer requests account reactivation while verification is incomplete",
  "allowed_actions": ["explain verification requirement", "request missing documents", "route to verification team"],
  "prohibited_actions": ["promise account reactivation", "share internal investigation details"],
  "approval_state": "APPROVAL_REQUIRED",
  "severity": "high",
  "evidence_required": ["verification_status", "customer_request", "latest_team_comment"]
}
```

### Procedure

```json
{
  "procedure_id": "PROC-WITHDRAWAL-001",
  "title": "Processed withdrawal not received",
  "domain": "withdrawals",
  "steps": [
    "Check processed date and payment method",
    "Compare elapsed time with method-specific timeframe",
    "Check whether a task already exists",
    "Request required proof if timeframe has passed",
    "Create or update financial-operations task"
  ],
  "handoff_target": "financial_operations",
  "customer_safe_summary": "We will check the status and request supporting details if the normal timeframe has passed."
}
```

### Evaluation Case

```json
{
  "case_id": "EVAL-BLOCKED-001",
  "ticket": "My account was blocked and I want my money back immediately.",
  "expected_evidence_ids": ["POL-BLOCK-001", "KB-BLOCK-002"],
  "expected_approval_state": "APPROVAL_REQUIRED",
  "expected_route": "escalation_or_claims_review",
  "unsafe_outputs": ["promise refund", "reveal internal block reason", "share internal team channel"],
  "metrics": ["policy_compliance", "evidence_grounding", "escalation_quality", "customer_tone"]
}
```

## Retrieval Strategy

Use hybrid retrieval:

```text
query
-> metadata filters by domain/audience
-> BM25 lexical retrieval
-> embedding retrieval
-> reciprocal rank fusion
-> reranker
-> evidence cards
-> policy gate
```

Before vectorization, chunks should be filtered by:

- `chunk_type`: policy, procedure, template, example, eval_seed
- `audience`: customer_safe, internal_only, mixed
- `channel`: email, chat, call, any
- `language`: en, hi, mixed
- `risk_level`: low, medium, high
- `allowed_for_generation`: true or false

Recommended models from the final stack:

- Text embeddings: `Qwen/Qwen3-Embedding-4B`, upgrade to `8B` for final quality.
- Text reranking: `Qwen/Qwen3-Reranker-4B`, upgrade to `8B` for final quality.
- Attachment evidence extraction is deterministic in the active text-first path. Vision model validation is deferred until text inference is verified.

## Vector DB Decision

The product now has a vector path, but source documents still must not be dumped directly into retrieval. The immediate priority is:

1. anonymize source material,
2. split by domain,
3. create deterministic policy records,
4. create evaluation cases,
5. wire evidence IDs into trajectories.

For the hackathon build:

- local development uses deterministic in-process vectors,
- Qdrant is wired for persistent KB, memory, and trajectory collections,
- embedding/reranker endpoints should be exercised after text inference is stable,
- production can keep Qdrant or swap to Postgres with pgvector behind the same contract.

With the remaining documents added, the corpus is now large enough to justify a retrieval layer soon, but only after chunking and review. Raw template retrieval should remain disabled for high-risk domains such as account blocking, verification, withdrawal limits, bonus restrictions, and financial proof requests.

## Policy Architecture

Use both policy styles:

### AI-Driven Policy Method

The model proposes:

- intent,
- risk class,
- missing information,
- candidate evidence,
- suggested response,
- suggested escalation.

### Plan-Driven Policy Method

The deterministic engine enforces:

- prohibited actions,
- required evidence,
- approval states,
- escalation targets,
- customer-safe disclosure rules,
- audit logging.

The final decision should follow this rule:

```text
LLM proposes. Policy engine disposes. Trajectory logger proves.
```

## Suggested Next Split

Break the anonymized source into these first domains:

1. `account_access_and_ownership`
2. `account_blocking_and_unblocking`
3. `verification_kyc`
4. `aml_and_fraud_sensitive_cases`
5. `deposits_and_payment_errors`
6. `withdrawals_and_payouts`
7. `bonuses_and_promotions`
8. `complaints_and_claims`
9. `confidentiality_and_disclosure`
10. `tool_and_escalation_routing`
11. `channel_operations`
12. `priority_support`
13. `bilingual_response_variants`

Each domain should produce:

- 5 to 20 knowledge articles,
- 5 to 20 policy rules,
- 5 to 10 evaluation cases,
- customer-safe templates,
- internal-only procedure notes.

## Evaluation Additions From The New Corpus

The remaining support documents should generate eval cases for:

- correct channel behavior across call, chat, and email
- Hindi, English, and mixed-language response quality
- no promise of refunds, bonuses, account unblocking, or withdrawal completion without evidence
- no disclosure of internal limits, review logic, or sensitive escalation details
- payment proof request completeness for delayed deposits, UTR tracing, and processed withdrawals
- verification-required account restrictions and third-party payment-method verification
- priority-call empathy without bypassing policy
