#!/usr/bin/env bash
# Start a vLLM server for one model, score the corpus through it, then stop the server.
#
# Usage:
#   scripts/run_scoring.sh <model-key> <hf-model-id> [port] [tensor-parallel] [extra `dti score` args...]
# Examples:
#   scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 1 --sample data/interim/pilot_50_seed0.csv
#   scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 2            # full corpus, 2 GPUs
#
# <model-key> must exist in configs/models.yaml. Scoring is resumable: rerun the same
# command after an interruption and only missing (occupation, run) pairs are scored.
set -euo pipefail

KEY=${1:?model key from configs/models.yaml}
HF_MODEL=${2:?Hugging Face model id}
PORT=${3:-8000}
TP=${4:-1}
shift $(( $# < 4 ? $# : 4 ))

mkdir -p logs
LOG="logs/vllm_${KEY}_$(date +%Y%m%d_%H%M%S).log"
echo "starting vLLM for ${HF_MODEL} on port ${PORT} (tp=${TP}), log: ${LOG}"
vllm serve "${HF_MODEL}" \
  --port "${PORT}" \
  --tensor-parallel-size "${TP}" \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --seed 0 \
  > "${LOG}" 2>&1 &
SERVER_PID=$!
trap 'kill ${SERVER_PID} 2>/dev/null || true' EXIT

for _ in $(seq 1 180); do
  if curl -sf "http://localhost:${PORT}/v1/models" > /dev/null; then break; fi
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then echo "vLLM exited early; see ${LOG}"; exit 1; fi
  sleep 10
done
curl -sf "http://localhost:${PORT}/v1/models" > /dev/null || { echo "vLLM not ready after 30 min; see ${LOG}"; exit 1; }

dti score --model "${KEY}" --base-url "http://localhost:${PORT}/v1" "$@"
