# Real AMD Developer Cloud Results

This file records the real AMD Developer Cloud run evidence captured during the hackathon session. The raw JSON benchmark files were generated inside the AMD notebook under `/workspace/AMD_Anirvium/amd/logs/`; this markdown file keeps the verified metrics in the GitHub submission even though generated JSON logs are ignored by default.

## Runtime Observed

The notebook allocation exposed one AMD GPU with approximately 48 GiB visible VRAM rather than the expected 192 GiB MI300X profile.

```text
ROCm driver: 6.16.13
GPU count: 1
GFX target: gfx1100
VRAM total: 51,522,830,336 bytes / 47.98 GiB
PyTorch: 2.9.1+gitff65f5b
vLLM: 0.16.1.dev0+g89a77b108.d20260318
torch.cuda.is_available(): True
```

## Model Serving Smoke Test

The vLLM/ROCm OpenAI-compatible endpoint was reachable at `http://localhost:8001/v1` using model alias `anirvium-text`.

```text
status: ok
base_url: http://localhost:8001/v1
model: anirvium-text
elapsed_ms: 1213
model_count: 1
```

Note: the raw model smoke response included a Qwen reasoning marker. The application path sanitizes raw thinking text before returning trajectory spans or final actions.

## Full Agent Trajectory Benchmark

Command shape:

```bash
python amd/benchmark_agent_eval.py \
  --mode llm \
  --dataset customer_support \
  --tickets 6 \
  --repeats 3
```

Observed result:

```text
benchmark_name: anirvium-agent-trajectory-eval
mode: llm
dataset: customer_support
provider: AMD Developer Cloud
backend: vLLM/ROCm
llm_base_url: http://localhost:8001/v1
llm_model: anirvium-text
repeats: 3
ticket_count: 6
agent_step_count: 13
tokens_per_second_avg: 72.53
tokens_per_second_max: 73.74
latency_seconds_avg: 190.1828
average_step_latency_ms: 14628.46
average_trajectory_score: 70.9
policy_compliance: 1.0
evidence_grounding: 1.0
```

Generated raw log on AMD notebook:

```text
/workspace/AMD_Anirvium/amd/logs/benchmark_llm_20260709210044.json
```

## Post-Policy-Fix Validation Run

After fixing customer-support policy compliance scoring, a smaller validation run confirmed the compliance metric remained correct.

Command shape:

```bash
python amd/benchmark_agent_eval.py \
  --mode llm \
  --dataset customer_support \
  --tickets 2 \
  --repeats 1
```

Observed result:

```text
ticket_count: 2
agent_step_count: 13
tokens_per_second_avg: 58.8
latency_seconds_avg: 117.9619
average_step_latency_ms: 9073.31
average_trajectory_score: 74.7
policy_compliance: 1.0
evidence_grounding: 1.0
token_efficiency: 0.798
```

Generated raw log on AMD notebook:

```text
/workspace/AMD_Anirvium/amd/logs/benchmark_llm_20260709212533.json
```

## Live Backend Run Proof

The AMD backend was run with:

```text
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:8001/v1
LLM_MODEL=anirvium-text
AMD_RUNTIME_PROFILE=text_48gb
```

Live `/runs` proof:

```text
run_id: run_20260710095313_ba7ce426
trajectory steps: 13
overall score: 72.0
policy_compliance: 1.0
evidence_grounding: 1.0
final_actions: 2
raw thinking leakage: none detected in application JSON
```

Graph discovery proof:

```text
graph_store: local_property_graph
nodes: 78
edges: 183
neo4j_status: optional_export_not_required_for_demo
sample_cypher_count: 8
```

## Claim Boundary

These results prove the text-first agent trajectory path ran against an AMD Developer Cloud GPU-backed vLLM endpoint. The judge-facing Docker path remains deterministic by default so the frontend can be evaluated reliably from GitHub without requiring private notebook access.
