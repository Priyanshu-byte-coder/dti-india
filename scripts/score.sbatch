#!/usr/bin/env bash
# SLURM template for the Nirma GPU cluster. Adjust partition, GPU count, time and
# environment activation to the cluster's setup before the first submit.
#
#   sbatch scripts/score.sbatch qwen32b Qwen/Qwen2.5-32B-Instruct
#
#SBATCH --job-name=dti-score
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=logs/slurm_%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs

# Activate the environment that has `pip install -e ".[gpu]"` (edit to match the cluster)
source .venv/bin/activate

export HF_HOME="${HF_HOME:-$PWD/.hf_cache}"
TP="${SLURM_GPUS_ON_NODE:-1}"
bash scripts/run_scoring.sh "${1:?model key}" "${2:?hf model id}" 8000 "${TP}" "${@:3}"
