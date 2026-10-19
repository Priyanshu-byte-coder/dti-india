#!/usr/bin/env bash
# Download the GGUF model files listed under `gguf:` in configs/models.yaml from Hugging
# Face into ../models (outside the repo). Hugging Face is reachable from PARAM Shavak;
# ollama.com and the conda channels are not.
#   bash scripts/shavak_models.sh            # all GGUF models
#   bash scripts/shavak_models.sh qwen14b    # one model
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
MODELS=${GGUF_DIR:-$ROOT/../models}
mkdir -p "$MODELS"
python -m pip install -q "huggingface_hub>=0.23"

python - "$MODELS" "$@" << 'EOF'
import sys, yaml
from huggingface_hub import hf_hub_download
out, wanted = sys.argv[1], set(sys.argv[2:])
models = yaml.safe_load(open("configs/models.yaml"))["models"]
for key, m in models.items():
    if "gguf" not in m or (wanted and key not in wanted):
        continue
    g = m["gguf"]
    print(f"{key}: {g['repo']} / {g['file']}", flush=True)
    path = hf_hub_download(g["repo"], g["file"], local_dir=out)
    print(f"  -> {path}", flush=True)
EOF
ls -lh "$MODELS"
