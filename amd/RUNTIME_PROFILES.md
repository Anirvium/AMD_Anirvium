# AMD Runtime Profiles

Use one heavyweight runtime profile at a time. The hackathon allocation may expose either the intended MI300X 192GB device or a smaller 48GB GPU profile. Verify VRAM before launching a model.

Text inference is the first validation target. Vision is intentionally deferred until the text trajectory benchmark has real AMD logs.

1. `text_48gb`: reliable Qwen3-8B support-agent planning/drafting profile for a 48GB runtime.
2. `text_48gb_14b`: target Qwen3-14B quality profile for a 48GB runtime.
3. `text`: full 192GB profile for Qwen3-30B-A3B.
4. `critic`: trajectory diagnosis and model-as-judge review on the full 192GB profile.
5. `embedding`: vectorization for KB, memory, and trajectory records.
6. `reranker`: final retrieval quality pass.

## Verify Visible GPU Memory

```bash
rocm-smi --showproductname --showmeminfo vram --showdriverversion
/opt/venv/bin/python - <<'PY'
import torch
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(i, p.name, round(p.total_memory / 1024**3, 2), "GiB")
PY
```

If the runtime reports roughly `47.98 GiB`, use `text_48gb`. If it reports roughly `192 GiB` and `gfx942`, use `text`.

## 48GB Reliable Text Profile

```bash
source /opt/venv/bin/activate
export PYTHON_BIN=/opt/venv/bin/python
export HF_HOME=/workspace/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PROFILE=text_48gb bash amd/run_runtime_profile.sh
```

Backend environment:

```bash
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_PROVIDER=openai_compatible
export LLM_MODEL=anirvium-text
export AMD_RUNTIME_PROFILE=text_48gb
```

This serves `Qwen/Qwen3-8B` as `anirvium-text`.

## 48GB Stretch Text Profile

Try this only after the Qwen3-8B smoke test and benchmark pass.

```bash
source /opt/venv/bin/activate
export PYTHON_BIN=/opt/venv/bin/python
export HF_HOME=/workspace/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PROFILE=text_48gb_14b bash amd/run_runtime_profile.sh
```

This serves `Qwen/Qwen3-14B` as `anirvium-text`. If it OOMs, go back to `text_48gb`.

## 192GB Text Profile

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

- 48GB target text: `Qwen/Qwen3-14B`
- 48GB reliable text: `Qwen/Qwen3-8B`
- 48GB emergency fallback: `Qwen/Qwen2.5-7B-Instruct`
- 192GB text: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Vision: deferred; attachment evidence uses deterministic metadata cards until the text benchmark is verified
- 48GB critic: reuse `anirvium-text` plus deterministic evaluator/diagnosis
- 192GB critic: `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
- 48GB retrieval: local deterministic vectors first; CPU `BAAI/bge-small-en-v1.5` or `intfloat/e5-small-v2` when dependencies are available
- 192GB retrieval: `Qwen/Qwen3-Embedding-4B` then `Qwen/Qwen3-Embedding-8B` for final quality
- 48GB reranking: deterministic/hybrid lexical reranking first
- 192GB reranking: `Qwen/Qwen3-Reranker-4B` then `Qwen/Qwen3-Reranker-8B` for final quality
- Safety model: deferred; deterministic policy gates and approval states are active now
