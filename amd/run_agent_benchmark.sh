#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${MODE:-mock}"
TICKETS="${TICKETS:-8}"
REPEATS="${REPEATS:-3}"
DATASET="${DATASET:-customer_support}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${ROOT_DIR}/.uv-cache}"

cd "${ROOT_DIR}"

if command -v uv >/dev/null 2>&1; then
  cd "${ROOT_DIR}/backend"
  uv run python ../amd/benchmark_agent_eval.py \
    --mode "${MODE}" \
    --tickets "${TICKETS}" \
    --repeats "${REPEATS}" \
    --dataset "${DATASET}"
else
  python amd/benchmark_agent_eval.py \
    --mode "${MODE}" \
    --tickets "${TICKETS}" \
    --repeats "${REPEATS}" \
    --dataset "${DATASET}"
fi
