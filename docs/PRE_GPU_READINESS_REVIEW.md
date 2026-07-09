# Pre-GPU Readiness Review

## Current Score

After the inference-readiness hardening pass, Anirvium AI is at:

```text
7.4 / 10 pre-GPU readiness
```

This is now stronger than a static judge prototype. The repo has a real customer-support dataset, curated KB layers, hybrid lexical/vector retrieval, optional Qdrant integration, memory collections, real LLM call paths, a vLLM smoke test, and a customer-support benchmark path.

It is still not a fully production-grade agent platform because real GPU inference, real multimodal extraction, durable storage, authentication, human approval workflows, and production observability have not been validated yet.

## What Is Ready

- Backend trajectory pipeline with 13 governed support-agent steps: planner, attachment evidence, triage, retrieval, policy, escalation, drafting, compliance, human handoff, critic, reflection, learning extraction, and optimizer.
- Curated customer-support KB layers:
  - policies
  - procedures
  - templates
  - eval cases
- Customer-support demo dataset aligned to the anonymized KB.
- Hybrid KB retrieval:
  - lexical JSON search
  - deterministic local vector fallback
  - optional Qdrant HTTP integration
- LLM generation hooks in:
  - response drafting
  - critic review
  - optimizer review
- AMD/vLLM smoke test:
  - `amd/smoke_vllm_openai.py`
- Customer-support benchmark path:
  - `DATASET=customer_support bash amd/run_agent_benchmark.sh`
- Agentic memory:
  - Redis-ready short-term memory
  - local fallback for deterministic tests
  - Qdrant/local vector long-term memory
  - Qdrant/local vector trajectory memory
- Frontend support for:
  - support KB demo
  - KB layer readiness
  - vector readiness
  - hybrid KB search

## What Still Requires GPU/Jupyter Validation

1. Start `PROFILE=text` on AMD Developer Cloud and smoke-test `/v1/models` plus `/chat/completions`.
2. Run backend with:

```bash
export LLM_PROVIDER=openai_compatible
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_MODEL=anirvium-text
export AMD_RUNTIME_PROFILE=text
```

3. Run:

```bash
python amd/smoke_vllm_openai.py --base-url http://localhost:8001/v1 --model anirvium-text
```

4. Run:

```bash
MODE=llm DATASET=customer_support TICKETS=6 REPEATS=3 bash amd/run_agent_benchmark.sh
```

5. Save real logs and screenshots under the AMD evidence paths listed in `amd/README_AMD_USAGE.md`.

## Remaining Gaps

- Image/video model loading is removed from the active GPU plan. Attachment evidence remains deterministic until text inference is verified.
- Qdrant is wired but not mandatory in local mock mode. For final demo, run Qdrant if the notebook supports Docker or use the local vector fallback.
- Embeddings currently use deterministic local vectors for pre-GPU readiness. Replace with Qwen embedding endpoint once the embedding profile is available.
- Human approval and escalation visibility is implemented for the demo, but a durable human task workflow is not productionized yet.
- Runs are stored as JSON files locally, not SQLite/Postgres.
- No authentication or tenant isolation.

## Updated Principal Score

| Area | Score |
| --- | ---: |
| Local demo readiness | 8.5/10 |
| Architecture quality | 8/10 |
| Real-use-case alignment | 7.5/10 |
| Inference readiness | 6.5/10 |
| GPU deployment readiness | 6.5/10 |
| Retrieval readiness | 7/10 |
| Frontend readiness | 7.5/10 |
| Production alignment | 4/10 |
| Competition readiness before real AMD run | 7.4/10 |

## Next Best Move

Push to GitHub, open the AMD notebook, run the text profile first, and validate the customer-support benchmark with real vLLM. Do not spend GPU time on image/video models until the text trajectory path has produced a real benchmark log.
