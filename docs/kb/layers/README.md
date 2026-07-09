# Curated KB Layers

The runtime layer records live in `backend/app/data/kb_layers/` so the FastAPI backend can load them directly.

Current layers:

- `policies.json`: deterministic policy gates, prohibited actions, approval states, and required evidence.
- `procedures.json`: internal and mixed-audience workflows that agents can follow but should not expose verbatim.
- `templates.json`: reviewed customer-safe response templates with variable slots and policy constraints.
- `eval_cases.json`: regression tickets for grounding, policy compliance, tone, bilingual behavior, and escalation correctness.

API access:

- `GET /kb/layers`
- `GET /kb/layers/{policies|procedures|templates|eval_cases}`
- `GET /kb/search?q=withdrawal%20processed`
- `GET /kb/vector/status`
- `POST /kb/vector/reindex`

Design rule: raw source material stays in `docs/kb/source_material/`; only reviewed layer records are allowed to influence retrieval and response drafting.

Vector behavior:

- Default local mode uses deterministic in-process vectors so tests and demos run without external services.
- Qdrant mode uses `VECTOR_BACKEND=qdrant`, `VECTOR_BASE_URL`, `VECTOR_KB_COLLECTION`, `VECTOR_MEMORY_COLLECTION`, and `VECTOR_TRAJECTORY_COLLECTION`.
- The vector layer is hybridized with lexical KB matching; policy gates still decide what the agent may do.
