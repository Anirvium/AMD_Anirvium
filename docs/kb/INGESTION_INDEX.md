# Knowledge Base Ingestion Index

This index tracks the anonymized customer-support corpus that should drive Anirvium AI's agentic intelligence layer.

## Source Sets

| Source set | Location | Files | Lines | Product role |
| --- | --- | ---: | ---: | --- |
| Core operations KB | `source_material/customer_support_operations_anonymized.md` | 1 | 1,720 | Primary policy/procedure source for account access, verification, deposits, withdrawals, blocking, escalation, and confidentiality. |
| Remaining support docs | `source_material/remaining_docs/` | 12 | 5,275 | Template bank, channel workflows, bilingual call/chat scripts, bonus rules, and scenario-specific examples. |

## Remaining Support Documents

| Document | Primary domains | Intended use |
| --- | --- | --- |
| `bonus.md` | bonuses, promotions, turnover, rewards, deposit-linked offers | Convert into customer-safe bonus articles, policy constraints, and eval cases for bonus removal, withdrawal impact, promo-code availability, and bonus cancellation. |
| `chat_document.md` | live chat, callback, verification, payment issues, tone | Convert into channel behavior rules for greeting, wait/hold handling, transfer, closure, callback expectations, and concise chat-safe responses. |
| `call_transcript.md` | voice support, Hindi/English call flow, deposit/withdrawal scripts | Use for call-agent tone, bilingual phrasing, verification before disclosure, empathy checkpoints, and voice-specific eval cases. |
| `customer_support_workflow.md` | calls, chats, emails, QA, prioritization, response structure | Use as the cross-channel operating model: severity classification, channel tone, email/chat structure, language quality rules, and QA scoring. |
| `templates_customer_concerns.md` | deposits, withdrawals, verification, account access, payment proofs, callback, complaints | Treat as the broad template reservoir. Split into reviewed template records only after attaching policy constraints and required evidence. |
| `templates_priority_calls_concern.md` | priority customer calls, deposits, withdrawals, verification, limits, payment proofs | Treat as high-touch escalation language. Do not use directly; convert into priority-channel templates with stricter approval and empathy requirements. |
| `batch_1.md` | deposits, USDT/USD limits, third-party payment verification, withdrawal methods | Mine for payment-method procedures, deposit waiting windows, withdrawal limits, and third-party source verification rules. |
| `batch_2.md` | deposits, withdrawals, verification, payment status, task follow-up | Mine for scenario-specific payment and verification templates; deduplicate against the large template bank. |
| `batch_3.md` | bank-card withdrawals, withdrawal fees, verification, reversal/status issues | Convert into withdrawal procedure variants and risk checks around fees, processed status, and verification-required unblocking. |
| `batch_4.md` | deposit cancellation, withdrawal fees, account access, password, withdrawal delays | Convert into account-access and payment exception templates, plus eval cases for "processed but not received" and "password incorrect". |
| `batch_5.md` | payment follow-up, verification, withdrawal/deposit exceptions | Use as supplementary examples for edge cases and Hindi/English response variants. |
| `batch_6.md` | UTR tracing, bonus reapply, KYC pending, payment-method verification | Convert into financial proof collection procedures and verification-blocked-account response rules. |

## Classification Rules

Every derived chunk should receive these fields before it is used by the agent:

```json
{
  "source_file": "source_material/remaining_docs/example.md",
  "chunk_type": "policy | procedure | template | example | eval_seed",
  "domain": "deposits | withdrawals | verification | account_access | bonuses | complaints | channel_ops",
  "audience": "customer_safe | internal_only | mixed",
  "channel": "email | chat | call | any",
  "language": "en | hi | mixed",
  "risk_level": "low | medium | high",
  "requires_evidence": true,
  "requires_approval": false,
  "allowed_for_generation": false
}
```

`allowed_for_generation` must stay `false` until the chunk has been reviewed, deduplicated, and attached to policy constraints.

## Immediate Product Decisions

- Keep the anonymized Markdown as source material; do not copy original DOCX files into the repo.
- Build deterministic policy records from the operations KB before exposing template text to the response generator.
- Use the template bank to create supervised response candidates and eval cases, not as raw prompt stuffing.
- Treat Hindi and mixed-language snippets as first-class language variants with their own evaluation cases.
- Treat priority-call material as escalation guidance, not a separate customer class hardcoded into the model.
- Require evidence cards before using payment-status, verification, account-blocking, bonus, or withdrawal-limit language.

## Next Derived Artifacts

1. `policies/`: deterministic rules for verification, payment delays, withdrawal limits, bonus restrictions, and disclosure limits. Seed implementation: `backend/app/data/kb_layers/policies.json`.
2. `procedures/`: channel-specific workflows for chat, call, email, callback, escalation, and financial task follow-up. Seed implementation: `backend/app/data/kb_layers/procedures.json`.
3. `templates/`: reviewed customer-safe templates with variable slots and prohibited-claim checks. Seed implementation: `backend/app/data/kb_layers/templates.json`.
4. `eval_cases/`: regression tickets for tone, evidence grounding, policy compliance, bilingual output, and escalation correctness. Seed implementation: `backend/app/data/kb_layers/eval_cases.json`.
