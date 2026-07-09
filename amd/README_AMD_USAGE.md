# AMD Developer Cloud Usage

Anirvium AI runs locally in deterministic mock mode and is prepared to switch to AMD Developer Cloud GPU-backed inference through vLLM/ROCm exposing an OpenAI-compatible API.

Use runtime profiles. Validate visible GPU memory before launch: some hackathon notebooks expose the intended MI300X 192GB device, while others may expose a smaller 48GB GPU profile. Vision is intentionally deferred until the text trajectory benchmark has real AMD logs.

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

For a 48GB runtime, start the reliable 7B profile:

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

Real AMD benchmark pending. Scripts and runbook are prepared. Sample files are marked as sample and are not claimed as verified AMD execution.

Current files:

- `amd/run_vllm_rocm.sh`: prepared vLLM/ROCm launch script.
- `amd/run_runtime_profile.sh`: prepared text, critic, embedding, and reranker runtime profile launcher. Image/video model loading is deferred.
- `amd/RUNTIME_PROFILES.md`: model profile instructions for 48GB and MI300X 192GB runtimes.
- `amd/run_agent_benchmark.sh`: prepared benchmark wrapper.
- `amd/benchmark_agent_eval.py`: prepared trajectory benchmark script.
- `amd/benchmark_results_sample.md`: sample-only local development values.
- `amd/logs/.gitkeep`: placeholder for future logs.
- `amd/screenshots/.gitkeep`: placeholder for future screenshots.

Future real evidence paths:

- `amd/logs/benchmark_amd_real_<date>.json`
- `amd/benchmark_results_real.md`
- `amd/screenshots/vllm_running.png`
- `amd/screenshots/benchmark_output.png`
- `amd/screenshots/dashboard_amd_panel.png`

## Claim Boundary

Do not present local mock results or sample values as verified AMD GPU execution. AMD proof should remain in the run logs, runbook, and submission evidence until real AMD Developer Cloud logs and screenshots are attached.
