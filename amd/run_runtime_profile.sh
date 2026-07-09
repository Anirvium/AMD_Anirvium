#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-text}"
PORT="${PORT:-8001}"

case "${PROFILE}" in
  text)
    export MODEL_ID="${MODEL_ID:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
    export SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-anirvium-text}"
    export MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
    export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.88}"
    ;;
  critic)
    export MODEL_ID="${MODEL_ID:-deepseek-ai/DeepSeek-R1-Distill-Qwen-32B}"
    export SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-anirvium-critic}"
    export MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
    export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.88}"
    ;;
  embedding)
    export MODEL_ID="${MODEL_ID:-Qwen/Qwen3-Embedding-4B}"
    export SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-anirvium-embedding}"
    export MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
    export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.72}"
    export VLLM_TASK="${VLLM_TASK:-embed}"
    ;;
  reranker)
    export MODEL_ID="${MODEL_ID:-Qwen/Qwen3-Reranker-4B}"
    export SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-anirvium-reranker}"
    export MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
    export GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.72}"
    export VLLM_TASK="${VLLM_TASK:-score}"
    ;;
  *)
    echo "Unknown PROFILE=${PROFILE}. Use text, critic, embedding, or reranker." >&2
    exit 2
    ;;
esac

export PORT

echo "Launching Anirvium AMD runtime profile: ${PROFILE}"
echo "Do not run all heavy profiles concurrently on one MI300X."
bash "$(dirname "${BASH_SOURCE[0]}")/run_vllm_rocm.sh"
