# Sourced by the nirma_* scripts: picks the model pair and tensor-parallel sizes from
# the GPUs (rule in configs/models.yaml and docs/decisions.md, item 3).
#   ~80 GB in total : qwen32b + llama8b
#   otherwise       : qwen7b  + llama8b   (each needs a ~24 GB card)
# Thresholds are 75 / 22 GB because cards report a little under their nominal size
# (an H100 80GB shows 79.6 GB, a 24 GB card 24.0 GB minus driver reserve).

mapfile -t _MEM < <(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
N_GPU=${#_MEM[@]}
GB_PER_GPU=$(( ($(printf '%s\n' "${_MEM[@]}" | sort -n | head -1) + 512) / 1024 ))

# smallest tensor-parallel size from 1/2/4/8 (at most the GPU count) giving >= $1 GB
_tp_for() {
  local need=$1 tp
  for tp in 1 2 4 8; do
    if (( tp <= N_GPU && tp * GB_PER_GPU >= need )); then echo "$tp"; return; fi
  done
  echo 0
}

PRIMARY_TP=$(_tp_for 75)
if (( PRIMARY_TP > 0 )); then
  PRIMARY_KEY=qwen32b; PRIMARY_HF=Qwen/Qwen2.5-32B-Instruct
else
  PRIMARY_KEY=qwen7b; PRIMARY_HF=Qwen/Qwen2.5-7B-Instruct; PRIMARY_TP=$(_tp_for 22)
fi
SECOND_KEY=llama8b; SECOND_HF=meta-llama/Llama-3.1-8B-Instruct; SECOND_TP=$(_tp_for 22)

if (( PRIMARY_TP == 0 || SECOND_TP == 0 )); then
  echo "GPUs too small: ${N_GPU} x ${GB_PER_GPU} GB; need at least 24 GB for a 7-8B model" >&2
  return 1 2> /dev/null || exit 1
fi
export N_GPU GB_PER_GPU PRIMARY_KEY PRIMARY_HF PRIMARY_TP SECOND_KEY SECOND_HF SECOND_TP
