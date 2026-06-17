#!/bin/bash
#SBATCH --job-name=package_hf_data
#SBATCH --account=dtn@cpu
#SBATCH --partition=prepost
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --time=06:00:00
#SBATCH --output=package_hf_data_%j.log
#SBATCH --error=package_hf_data_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATASETS_ROOT="${DATASETS_ROOT:-$SCRATCH/datasets/datatondatasets}"
HF_DATASET="${HF_DATASET:-mimic}"
HF_PACKAGE_ROOT="${HF_PACKAGE_ROOT:-$WORK/hf_upload_ready}"
HF_IMAGES_PER_SHARD="${HF_IMAGES_PER_SHARD:-5000}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}/scripts"
if [ ! -f "$SCRIPT_DIR/package_hf_dataset.py" ]; then
    echo "Could not find $SCRIPT_DIR/package_hf_dataset.py"
    echo "Submit this job from the datathon repository root."
    exit 1
fi

python "$SCRIPT_DIR/package_hf_dataset.py" \
    --datasets-root "$DATASETS_ROOT" \
    --output-root "$HF_PACKAGE_ROOT" \
    --dataset "$HF_DATASET" \
    --images-per-shard "$HF_IMAGES_PER_SHARD" \
    --overwrite
