# AMD Developer Cloud Usage

Anirvium AI runs locally in deterministic mock mode and has also executed against AMD Developer Cloud GPU-backed inference through vLLM/ROCm exposing an OpenAI-compatible API.

Use runtime profiles and validate visible GPU memory before launch. The verified event session exposed approximately 47.98 GiB and `gfx1100`; the 192GB MI300X configuration remains a target profile, not a measured result. Vision remains deferred in the text-first product path.

## A. AMD GPU Runbook

### 1. Start vLLM/ROCm

On the AMD Developer Cloud GPU machine, first check visible VRAM:

```bash
rocm-smi --showproductname --showmeminfo vram --showdriverversion
/opt/venv/bin/python - <<'PY'
import torch
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(i, p.name, round(p.total_memory / 1024**3, 2), "GiB")
PY
```

For a 48GB runtime, start the reliable Qwen3-8B profile:

```bash
source /opt/venv/bin/activate
export PYTHON_BIN=/opt/venv/bin/python
export HF_HOME=/workspace/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PROFILE=text_48gb bash amd/run_runtime_profile.sh
```

For a confirmed MI300X 192GB runtime, start the full profile:

```bash
source /opt/venv/bin/activate
export PYTHON_BIN=/opt/venv/bin/python
PROFILE=text bash amd/run_runtime_profile.sh
```

The script starts an OpenAI-compatible server at:

```text
http://localhost:8001/v1
```

### 2. Set LLM Environment Variables

```bash
export LLM_BASE_URL=http://localhost:8001/v1
export LLM_API_KEY=dummy
export LLM_MODEL=anirvium-text
export LLM_PROVIDER=openai_compatible
export AMD_RUNTIME_PROFILE=text_48gb
```

For critic/model-as-judge review:

```bash
PROFILE=critic bash amd/run_runtime_profile.sh
```

For vector retrieval quality after the text benchmark:

```bash
PROFILE=embedding bash amd/run_runtime_profile.sh
PROFILE=reranker bash amd/run_runtime_profile.sh
```

### 3. Run The Agent Benchmark

First smoke-test the vLLM endpoint:

```bash
python amd/smoke_vllm_openai.py --base-url http://localhost:8001/v1 --model anirvium-text
```

```bash
LLM_BASE_URL=http://localhost:8001/v1 \
LLM_API_KEY=dummy \
LLM_MODEL=anirvium-text \
MODE=llm \
DATASET=customer_support \
TICKETS=6 \
REPEATS=3 \
bash amd/run_agent_benchmark.sh
```

### 4. Save Logs

The benchmark automatically writes JSON logs under:

```text
amd/logs/
```

For the final verified AMD run, save or rename the real log as:

```text
amd/logs/benchmark_amd_real_<date>.json
```

Also create a human-readable real results summary after the run:

```text
amd/benchmark_results_real.md
```

### 5. Capture Screenshots

Capture:

- `amd/screenshots/vllm_running.png`
- `amd/screenshots/benchmark_output.png`
- `amd/screenshots/dashboard_amd_panel.png`

The screenshots should show the vLLM/ROCm server, benchmark output, and the dashboard AMD panel after real values are attached.

### 6. Metrics To Record

- tokens/sec
- latency
- throughput
- number of support tickets processed
- number of agent steps evaluated
- average trajectory score
- evidence grounding
- policy compliance
- token efficiency

## B. Current Evidence Status

The text-first AMD benchmark and live backend run were completed. The durable committed evidence is [benchmark_results_real.md](benchmark_results_real.md). Raw JSON logs were generated inside the ephemeral AMD notebook and were ignored by Git; do not cite those uncommitted paths as judge-accessible artifacts.

Current files:

- `amd/run_vllm_rocm.sh`: prepared vLLM/ROCm launch script.
- `amd/run_runtime_profile.sh`: prepared text, critic, embedding, and reranker runtime profile launcher. Image/video model loading is deferred.
- `amd/RUNTIME_PROFILES.md`: model profile instructions for 48GB and MI300X 192GB runtimes.
- `amd/run_agent_benchmark.sh`: prepared benchmark wrapper.
- `amd/benchmark_agent_eval.py`: prepared trajectory benchmark script.
- `amd/benchmark_results_sample.md`: sample-only local development values.
- `amd/benchmark_results_real.md`: verified human-readable AMD execution evidence.
- `amd/logs/.gitkeep`: placeholder; raw notebook logs are not committed.

Observed verified path:

- `Qwen/Qwen3-8B` served as `anirvium-text`.
- OpenAI-compatible vLLM endpoint on ROCm.
- Approximately 47.98 GiB visible VRAM and `gfx1100` runtime target.
- Thirteen-step Sarvagun/SuperTuriya execution through the live backend.
- Detailed metrics and claim boundaries in `amd/benchmark_results_real.md`.

## Claim Boundary

Do not present local mock results, sample values, or the 192GB target profile as verified AMD execution. The real claim is limited to the text-first Qwen3-8B/vLLM/ROCm path summarized in `amd/benchmark_results_real.md`. The application did not run an official Track 3 performance benchmark.
