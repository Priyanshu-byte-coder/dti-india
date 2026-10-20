#!/usr/bin/env bash
# Everything after the full LLM scoring run, in order. Run from the repo root on the
# machine that holds data/llm/ and data/raw/plfs/ (PARAM Shavak: ~/priyanshu/dti-india).
#
#   bash scripts/post_run.sh            # all steps
#   bash scripts/post_run.sh human      # only re-run reliability after coder forms arrive
#
# Main instrument: qwen14b, strict rubric (prompt hash 46a323537a); llama8b_gguf is the
# second model family for cross-model agreement. See docs/decisions.md (2026-10-20).
set -euo pipefail
PV=46a323537a
MAIN=qwen14b
SECOND=llama8b_gguf
PY=${PY:-python}
mkdir -p logs/tmp
export TMPDIR="$PWD/logs/tmp"   # the system disk (/tmp) on PARAM Shavak can be full

step() { echo; echo "== $*"; }

if [[ "${1:-all}" == "human" ]]; then
  step "RQ1 reliability incl. human forms in data/human/"
  dti reliability
  exit 0
fi

step "RQ1: consensus + DTI for the NCO corpus (both models)"
dti aggregate --corpus nco --models "$MAIN" "$SECOND" --prompt-version "$PV"
step "RQ1: run stability, cross-model and (if forms are present) human agreement"
dti reliability
step "Keyword benchmark on NCO text"
dti baseline

step "RQ2: same prompt on O*NET text, then India vs O*NET gap"
dti aggregate --corpus onet --models "$MAIN" --prompt-version "$PV"
dti gap --model "$MAIN" --prompt-version "$PV"

step "RQ3-RQ4: PLFS with the LLM DTI (main model)"
dti plfs-build --model "$MAIN" --prompt-version "$PV" --out data/processed/plfs_${MAIN}.parquet
dti analysis --input data/processed/plfs_${MAIN}.parquet --out reports/econ_llm

step "Robustness: second model family, baseline + robustness only"
dti plfs-build --model "$SECOND" --prompt-version "$PV" --out data/processed/plfs_${SECOND}.parquet
dti analysis --input data/processed/plfs_${SECOND}.parquet --out reports/econ_llm_${SECOND} --skip dml cqr rif heckman oaxaca grf_input

step "Paper tables"
$PY paper/make_tables.py reports/econ_llm "NCO-LLM DTI (${MAIN})" paper/tables_llm.md
echo "done. Copy reports/ and paper/tables_llm.md back and update paper/draft.md ([PENDING-LLM])."
