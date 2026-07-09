# Anirvium Knowledge Base

This directory contains anonymized source material for building Anirvium AI's customer-support trajectory intelligence layer.

## Current Source

- `source_material/customer_support_operations_anonymized.md`
- `source_material/remaining_docs/`
- `INGESTION_INDEX.md`
- `layers/README.md`

The core operations document is an anonymized operations knowledge base for a regulated customer-support environment. It covers account access, account blocking, verification/KYC, AML-adjacent workflows, deposits, withdrawals, payment errors, bonus handling, escalation workflows, customer communication rules, internal task routing, and confidentiality requirements.

The remaining support documents add 12 anonymized source files covering support templates, priority-call handling, live chat workflows, call scripts, bonus FAQs, Hindi/English response variants, payment proof collection, UTR tracing, callback handling, and channel-level quality rules.

## Anonymization

The source material was anonymized before being added to the repo.

Removed or generalized:

- specific company/platform names
- affiliate/partner brand names
- internal CRM/tool names
- team-chat/channel names
- task portal and internal knowledge-base links
- internal and public URLs tied to the source company
- department email addresses
- example customer email addresses
- named support staff and example personal identifiers
- source-specific DOCX filenames that exposed internal labels

The source-specific anonymization script was not retained in the repo because it contained the original sensitive identifiers as replacement patterns.

## Intended Product Use

This material should be treated as domain knowledge for:

- policy-aware support-agent planning
- evidence retrieval
- escalation routing
- approval-state decisions
- deterministic evaluator tests
- failure diagnosis and optimizer recommendations
- synthetic scenario generation

It should not be treated as executable policy until it is broken into structured, reviewable policy records.

## Recommended KB Layers

1. `source_material/`
   Raw anonymized documents and transcripts. These are source-of-truth inputs, not direct prompt material.

2. `articles/`
   Cleaned knowledge articles split by domain, such as verification, deposits, withdrawals, account blocking, and complaints.

3. `policies/`
   Deterministic rules with IDs, severity, allowed actions, approval states, and escalation targets. Runtime seed records currently live in `backend/app/data/kb_layers/policies.json`.

4. `procedures/`
   Step-by-step support workflows that agents can follow. Runtime seed records currently live in `backend/app/data/kb_layers/procedures.json`.

5. `templates/`
   Customer-safe response templates with required variables and policy constraints. Runtime seed records currently live in `backend/app/data/kb_layers/templates.json`.

6. `eval_cases/`
   Test tickets, expected evidence IDs, expected approval state, expected route, and known failure modes. Runtime seed records currently live in `backend/app/data/kb_layers/eval_cases.json`.

7. `connectors/`
   API/tool discovery specs for CRM, ticketing, billing, identity verification, and knowledge systems.

## Vector Database Recommendation

Use vector search only over reviewed chunks. Do not make vector search the only source of truth.

Recommended path:

- Now: keep anonymized documents as source material and derive structured rules/evaluation cases.
- Current runtime: use hybrid lexical/vector retrieval over curated KB layer records.
- Local mode: deterministic in-process vectors for offline development and repeatable tests.
- GPU/Qdrant mode: switch to Qdrant-backed collections for KB, memory, and trajectory records.
- Production path: keep Qdrant or Postgres/pgvector behind the same retrieval contract.

The policy engine should remain deterministic for high-risk actions. Retrieval should supply evidence; policy rules should decide what the agent may do.
