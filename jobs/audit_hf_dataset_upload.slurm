#!/bin/bash
#SBATCH --job-name=audit_hf_data
#SBATCH --account=dtn@cpu
#SBATCH --partition=prepost
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --hint=nomultithread
#SBATCH --time=01:00:00
#SBATCH --output=audit_hf_data_%j.log
#SBATCH --error=audit_hf_data_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

if ! hf auth whoami >/dev/null 2>&1; then
    echo "Hugging Face authentication is not configured."
    echo "Run 'hf auth login' once, or submit this job with HF_TOKEN set."
    exit 1
fi

DATASETS_ROOT="${DATASETS_ROOT:-$SCRATCH/datasets/datatondatasets}"
HF_DATASET="${HF_DATASET:-mimic}"
OUTPUT_DIR="${HF_AUDIT_OUTPUT_DIR:-$WORK/hf_upload_audits}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}/scripts"
if [ ! -f "$SCRIPT_DIR/audit_hf_dataset_upload.py" ]; then
    echo "Could not find $SCRIPT_DIR/audit_hf_dataset_upload.py"
    echo "Submit this job from the datathon repository root."
    exit 1
fi

python "$SCRIPT_DIR/audit_hf_dataset_upload.py" \
    --datasets-root "$DATASETS_ROOT" \
    --dataset "$HF_DATASET" \
    --output-dir "$OUTPUT_DIR"
