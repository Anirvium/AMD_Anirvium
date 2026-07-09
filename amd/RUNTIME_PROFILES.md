# AMD Runtime Profiles

Use one heavyweight runtime profile at a time on the single MI300X 192GB notebook.

Text inference is the first validation target. Vision is intentionally deferred until the text trajectory benchmark has real AMD logs.

1. `text`: support-agent planning, drafting, optimizer recommendations.
2. `critic`: trajectory diagnosis and model-as-judge review.
3. `embedding`: vectorization for KB, memory, and trajectory records.
4. `reranker`: final retrieval quality pass.

## Text Profile

```bash
PROFILE=text bash amd/run_runtime_profile.sh
```

Backend environment:

```bash
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_PROVIDER=openai_compatible
export LLM_MODEL=anirvium-text
export AMD_RUNTIME_PROFILE=text
```

## Critic Profile

```bash
PROFILE=critic bash amd/run_runtime_profile.sh
```

Backend environment:

```bash
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_PROVIDER=openai_compatible
export LLM_MODEL=anirvium-critic
export AMD_RUNTIME_PROFILE=critic
```

## Embedding Profile

```bash
PROFILE=embedding bash amd/run_runtime_profile.sh
```

Backend/vector environment:

```bash
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_EMBEDDING_MODEL=anirvium-embedding
export AMD_RUNTIME_PROFILE=embedding
```

## Reranker Profile

```bash
PROFILE=reranker bash amd/run_runtime_profile.sh
```

Backend/vector environment:

```bash
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_RERANKER_MODEL=anirvium-reranker
export AMD_RUNTIME_PROFILE=reranker
```

## Final Stack

- Text: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Vision: deferred; attachment evidence uses deterministic metadata cards until the text benchmark is verified
- Critic: `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
- Text retrieval: `Qwen/Qwen3-Embedding-4B` then `Qwen/Qwen3-Embedding-8B` for final quality
- Text reranking: `Qwen/Qwen3-Reranker-4B` then `Qwen/Qwen3-Reranker-8B` for final quality
- Safety model: deferred; deterministic policy gates and approval states are active now
