#!/usr/bin/env bash
# One-time setup on the Nirma GPU server. Run from the repo root:
#   bash scripts/nirma_setup.sh
# Creates .venv, installs the GPU extras, runs the tests, and writes the GPU spec and
# the model pair it implies to logs/gpu_spec.txt.
set -euo pipefail

mkdir -p logs
PY=""
for c in python3.12 python3.11 python3.10 python3; do
  if command -v "$c" > /dev/null && "$c" -c 'import sys; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 12))'; then
    PY=$c; break
  fi
done
[ -n "$PY" ] || { echo "need Python 3.10-3.12 (vLLM does not support newer yet)"; exit 1; }

[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e ".[dev,gpu]"
pytest -q

source scripts/nirma_models.sh
{
  echo "# $(date -Is) $(hostname)"
  nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
  echo "gpus=${N_GPU} min_gb_per_gpu=${GB_PER_GPU}"
  echo "primary=${PRIMARY_KEY} (${PRIMARY_HF}, tp=${PRIMARY_TP})"
  echo "second=${SECOND_KEY} (${SECOND_HF}, tp=${SECOND_TP})"
} | tee logs/gpu_spec.txt

if [ -z "${HF_TOKEN:-}" ] && ! [ -s "${HF_HOME:-$HOME/.cache/huggingface}/token" ]; then
  echo "NOTE: no Hugging Face token. Llama is gated: accept the licence at"
  echo "  https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct  and run  huggingface-cli login"
fi
