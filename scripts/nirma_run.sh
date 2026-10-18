#!/usr/bin/env bash
# Run one stage of the GPU pipeline on the Nirma server, detached (tmux, or nohup when
# tmux is missing) so it survives a dropped SSH connection. From the repo root:
#   bash scripts/nirma_run.sh pilot     # 50 occupations, both rubrics, both models (HANDOFF step 2)
#   bash scripts/nirma_run.sh full      # 3,450 occupations, both models (step 3)
#   bash scripts/nirma_run.sh onet      # O*NET corpus with the primary model, then the gap (steps 4-5)
# Check progress with  bash scripts/status.sh. Rerunning a stage resumes it.
# RUBRIC=configs/rubric_strict.yaml bash scripts/nirma_run.sh full   scores with the strict variant.
set -euo pipefail

STAGE=${1:?stage: pilot | full | onet}
SESSION="dti-${STAGE}"
LOG="logs/run_${STAGE}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

PIDFILE="logs/run_${STAGE}.pid"
if [ -z "${DTI_DETACHED:-}" ]; then
  if tmux has-session -t "$SESSION" 2> /dev/null || { [ -s "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2> /dev/null; }; then
    echo "stage '${STAGE}' is already running; see bash scripts/status.sh"; exit 1
  fi
  if command -v tmux > /dev/null; then
    tmux new-session -d -s "$SESSION" "DTI_DETACHED=1 bash $0 $* 2>&1 | tee ${LOG}"
    echo "started '${STAGE}' in tmux session ${SESSION} (attach: tmux attach -t ${SESSION}), log ${LOG}"
  else
    DTI_DETACHED=1 setsid nohup bash "$0" "$@" > "$LOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE"
    echo "started '${STAGE}' in the background (pid $!), log ${LOG}"
  fi
  exit 0
fi

source .venv/bin/activate
export HF_HOME="${HF_HOME:-$PWD/.hf_cache}"
source scripts/nirma_models.sh
# Do not crowd out other lab jobs: stop if a GPU already has more than 2 GB in use.
busy=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 > 2048')
if [ -n "$busy" ] && [ -z "${FORCE:-}" ]; then
  echo "GPUs in use by other jobs (index, MiB used):"; echo "$busy"; echo "wait, or rerun with FORCE=1"; exit 1
fi
RUBRIC=${RUBRIC:-configs/rubric.yaml}
PILOT=data/interim/pilot_50_seed0.csv
version() { dti prompt --limit 1 --rubric "$1" | head -1 | awk '{print $NF}'; }
score() { bash scripts/run_scoring.sh "$1" "$2" 8000 "$3" "${@:4}"; }
echo "== ${STAGE} $(date -Is): primary ${PRIMARY_KEY} tp=${PRIMARY_TP}, second ${SECOND_KEY} tp=${SECOND_TP}"

case "$STAGE" in
  pilot)
    for r in configs/rubric.yaml configs/rubric_strict.yaml; do
      score "$PRIMARY_KEY" "$PRIMARY_HF" "$PRIMARY_TP" --sample "$PILOT" --rubric "$r"
      score "$SECOND_KEY" "$SECOND_HF" "$SECOND_TP" --sample "$PILOT" --rubric "$r"
    done
    dti aggregate --models "$PRIMARY_KEY" "$SECOND_KEY"
    dti reliability
    ;;
  full)
    score "$PRIMARY_KEY" "$PRIMARY_HF" "$PRIMARY_TP" --rubric "$RUBRIC"
    score "$SECOND_KEY" "$SECOND_HF" "$SECOND_TP" --rubric "$RUBRIC"
    dti aggregate --models "$PRIMARY_KEY" "$SECOND_KEY" --prompt-version "$(version "$RUBRIC")"
    dti baseline
    dti reliability
    ;;
  onet)
    score "$PRIMARY_KEY" "$PRIMARY_HF" "$PRIMARY_TP" --corpus onet --rubric "$RUBRIC"
    dti aggregate --corpus onet --models "$PRIMARY_KEY" --prompt-version "$(version "$RUBRIC")"
    dti gap --model "$PRIMARY_KEY" --prompt-version "$(version "$RUBRIC")"
    ;;
  *) echo "unknown stage ${STAGE}"; exit 1 ;;
esac
echo "== ${STAGE} finished $(date -Is)"
