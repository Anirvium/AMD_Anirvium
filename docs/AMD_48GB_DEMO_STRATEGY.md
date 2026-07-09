# AMD 48GB Demo Strategy

## Situation

The observed AMD notebook may expose a 48GB `gfx1100` GPU instead of the intended MI300X 192GB `gfx942` allocation. When visible VRAM is roughly 48GB, do not launch the 30B MoE profile. Use the 48GB path below and keep the full MI300X stack as the upgrade path if the correct allocation becomes available.

## Required Hardware Check

```bash
rocm-smi --showproductname --showmeminfo vram --showdriverversion
/opt/venv/bin/python - <<'PY'
import torch
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(i, p.name, round(p.total_memory / 1024**3, 2), "GiB")
PY
```

Use `PROFILE=text_48gb` when the runtime reports roughly 48GB.
Use `PROFILE=text` only when the runtime reports roughly 192GB and `gfx942`.

## Model Ranking For 48GB

1. `Qwen/Qwen3-14B` BF16 or quantized via vLLM
   - Target quality model for the final 48GB demo.
   - Use after the Qwen3-8B smoke test and benchmark pass.
   - Use `MAX_MODEL_LEN=8192` and conservative GPU utilization.
   - Fall back to Qwen3-8B immediately if loading is unstable.

2. `Qwen/Qwen3-8B` BF16 via vLLM
   - Guaranteed-path model for smoke test, benchmark, backend, and dashboard.
   - Best reliability-quality balance on the observed 48GB runtime.
   - Strong enough because Anirvium's product value is orchestration, evidence, policy, handoff, evaluation, and learning extraction rather than raw chatbot size.

3. `Qwen/Qwen2.5-7B-Instruct`
   - Emergency fallback if Qwen3 chat templates or ROCm/vLLM behavior cause friction.

4. Quantized 14B variants, if already available in the AMD image
   - AWQ or FP8 may help, but quantization kernel support can vary across ROCm/vLLM builds.
   - Do not spend hackathon time debugging quantization unless Qwen3-8B proof is already complete.

5. `Qwen/Qwen3-30B-A3B-Instruct-2507`
   - Reserved for confirmed MI300X 192GB.
   - Do not run on a 48GB allocation.

## 48GB Product Architecture

- Text generation: vLLM serving `anirvium-text` with Qwen3-8B or Qwen3-14B.
- Critic/evaluator: deterministic evaluator plus optional same-model critique through `anirvium-text`.
- Retrieval: existing hybrid lexical/local-vector path.
- Embeddings: local deterministic vectors now; add CPU `BAAI/bge-small-en-v1.5` or `intfloat/e5-small-v2` when dependencies are available.
- Reranking: deterministic/hybrid scoring for the demo; GPU reranker is optional after text proof.
- Policy/safety: deterministic compliance agent, approval states, human handoff, and risk flags.
- Graph discovery: local property graph export now; Neo4j is optional for post-run discovery and advanced visualization.
- Learning loop: reflection and learning extraction agents remain active without extra GPU models.
- Vision: deferred; attachment evidence cards remain deterministic.

## External API Key Policy

Do not make OpenAI, Claude, or any external hosted LLM API a required demo dependency unless the hackathon rules explicitly allow it. Use external APIs only as a clearly disclosed optional fallback, because the strongest AMD submission should prove the core agent loop on AMD/vLLM.

If organizers explicitly permit external APIs, the safest fallback is:

- AMD/vLLM for the visible demo and benchmark evidence.
- External API only for optional judge/critic comparison, never for the main claimed AMD run.

## Launch Commands

Reliable 48GB profile:

```bash
source /opt/venv/bin/activate
export PYTHON_BIN=/opt/venv/bin/python
export HF_HOME=/workspace/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PROFILE=text_48gb bash amd/run_runtime_profile.sh
```

Stretch 48GB profile:

```bash
source /opt/venv/bin/activate
export PYTHON_BIN=/opt/venv/bin/python
export HF_HOME=/workspace/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PROFILE=text_48gb_14b bash amd/run_runtime_profile.sh
```

Benchmark:

```bash
source backend/.venv/bin/activate
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_MODEL=anirvium-text
export LLM_PROVIDER=openai_compatible
export AMD_RUNTIME_PROFILE=text_48gb
python amd/benchmark_agent_eval.py --mode llm --dataset customer_support --tickets 6 --repeats 3
```
