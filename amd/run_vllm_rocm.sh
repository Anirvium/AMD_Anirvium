#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-mistralai/Mistral-7B-Instruct-v0.3}"
PORT="${PORT:-8001}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-${MODEL_ID}}"
VLLM_TASK="${VLLM_TASK:-}"
VLLM_QUANTIZATION="${VLLM_QUANTIZATION:-}"
PYTHON_BIN="${PYTHON_BIN:-python}"

echo "Starting OpenAI-compatible vLLM server on ROCm"
echo "Model: ${MODEL_ID}"
echo "Served model name: ${SERVED_MODEL_NAME}"
echo "Port: ${PORT}"

TASK_ARGS=()
if [[ -n "${VLLM_TASK}" ]]; then
  TASK_ARGS=(--task "${VLLM_TASK}")
  echo "Task: ${VLLM_TASK}"
fi

QUANTIZATION_ARGS=()
if [[ -n "${VLLM_QUANTIZATION}" ]]; then
  QUANTIZATION_ARGS=(--quantization "${VLLM_QUANTIZATION}")
  echo "Quantization: ${VLLM_QUANTIZATION}"
fi

"${PYTHON_BIN}" -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --model "${MODEL_ID}" \
  --served-model-name "${SERVED_MODEL_NAME}" \
  "${TASK_ARGS[@]}" \
  "${QUANTIZATION_ARGS[@]}" \
  --dtype bfloat16 \
  --max-model-len "${MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --trust-remote-code
