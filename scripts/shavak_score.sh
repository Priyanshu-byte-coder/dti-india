#!/usr/bin/env bash
# PARAM Shavak (Nirma): serve one GGUF model with llama.cpp on the Quadro GP100, score
# through it, then stop the server. vLLM cannot run here (Pascal GPU, CentOS 7), so this
# replaces scripts/run_scoring.sh on this machine. Same OpenAI-compatible endpoint, same
# prompt and schema, so the output is identical in format.
#
#   bash scripts/shavak_score.sh <model-key> [extra `dti score` args...]
#   bash scripts/shavak_score.sh qwen14b --sample data/interim/pilot_50_seed0.csv
#
# <model-key> must have a `gguf:` entry in configs/models.yaml. Resumable like `dti score`.
set -euo pipefail

KEY=${1:?model key from configs/models.yaml}
shift
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LLAMA=${LLAMA_CPP_DIR:-$ROOT/../llama.cpp}
MODELS=${GGUF_DIR:-$ROOT/../models}
PORT=${PORT:-8090}
SLOTS=${SLOTS:-4}                 # parallel sequences in llama.cpp (continuous batching)
CTX_PER_SLOT=${CTX_PER_SLOT:-5120}
GPU=${GPU:-}                      # empty = pick the largest-memory GPU (the GP100)

GGUF=$(python - "$KEY" << 'EOF'
import sys, yaml
m = yaml.safe_load(open("configs/models.yaml"))["models"][sys.argv[1]]
print(m["gguf"]["file"])
EOF
)
[ -f "$MODELS/$GGUF" ] || { echo "model file missing: $MODELS/$GGUF (run scripts/shavak_models.sh)"; exit 1; }

if [ -z "$GPU" ]; then
  GPU=$(nvidia-smi --query-gpu=index,memory.total --format=csv,noheader,nounits | sort -t, -k2 -n -r | head -1 | cut -d, -f1)
fi
# nvidia-smi numbers GPUs by PCI bus; make CUDA use the same numbering
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=$GPU
# llama.cpp was built with gcc 9.1 and CUDA 12.2; the system libstdc++ (gcc 4.8) is too old
export LD_LIBRARY_PATH=/opt/gcc-9.1.0/lib64:/usr/local/cuda-12.2/lib64:${LD_LIBRARY_PATH:-}

mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/llama_${KEY}_$(date +%Y%m%d_%H%M%S).log"
echo "llama.cpp: $GGUF on GPU $GPU, port $PORT, $SLOTS slots, log $LOG"
"$LLAMA/build/bin/llama-server" -m "$MODELS/$GGUF" --port "$PORT" --host 127.0.0.1 \
  -ngl 999 -np "$SLOTS" -c $((SLOTS * CTX_PER_SLOT)) --seed 0 > "$LOG" 2>&1 &
SERVER_PID=$!
trap 'kill ${SERVER_PID} 2>/dev/null; wait ${SERVER_PID} 2>/dev/null || true' EXIT

for _ in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null; then break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then echo "llama-server exited early; see $LOG"; tail -20 "$LOG"; exit 1; fi
  sleep 5
done
curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null || { echo "llama-server not ready after 10 min; see $LOG"; exit 1; }

cd "$ROOT"
dti score --model "$KEY" --base-url "http://127.0.0.1:${PORT}/v1" --concurrency "$SLOTS" "$@"
