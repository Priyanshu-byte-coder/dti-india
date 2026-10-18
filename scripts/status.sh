#!/usr/bin/env bash
# One-screen progress report for runs on the GPU server (what Claude checks over SSH):
#   bash scripts/status.sh
cd "$(dirname "$0")/.."

echo "== GPUs"
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader 2> /dev/null || echo "nvidia-smi not available"

echo "== running stages"
running=$(tmux ls 2> /dev/null | grep '^dti-')
for f in logs/run_*.pid; do
  [ -s "$f" ] && kill -0 "$(cat "$f")" 2> /dev/null && running+=$'\n'"$(basename "$f" .pid) (pid $(cat "$f"))"
done
[ -n "${running//$'\n'/}" ] && echo "${running#$'\n'}" || echo "no dti stage running"

echo "== scoring output (model/prompt/corpus: records, ok, failed, distinct occupations)"
for f in data/llm/*/*/*.jsonl; do
  [ -e "$f" ] || { echo "none yet"; break; }
  python3 - "$f" << 'EOF'
import json, sys
path = sys.argv[1]
n = ok = 0
codes = set()
with open(path, encoding="utf-8") as fh:
    for line in fh:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        n += 1
        ok += bool(rec.get("ok"))
        codes.add(rec.get("code"))
model, version, corpus = path.split("/")[-3], path.split("/")[-2], path.split("/")[-1][:-6]
print(f"{model}/{version}/{corpus}: {n} records, {ok} ok, {n - ok} failed, {len(codes)} occupations")
EOF
done

echo "== latest run log"
LOG=$(ls -t logs/run_*.log 2> /dev/null | head -1)
if [ -n "$LOG" ]; then echo "$LOG"; tail -n 8 "$LOG"; else echo "none"; fi

echo "== latest vLLM log (errors)"
VLOG=$(ls -t logs/vllm_*.log 2> /dev/null | head -1)
if [ -n "$VLOG" ]; then
  echo "$VLOG"
  errs=$(grep -iE "error|out of memory|traceback|killed" "$VLOG" | tail -n 5)
  echo "${errs:-no errors}"
else
  echo "none"
fi
