#!/bin/bash
#SBATCH --job-name=taix_ray
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=20:00:00
#SBATCH --output=taix_ray_%j.log
#SBATCH --error=taix_ray_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-0}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
OUTPUT_DIR="${TAIX_RAY_OUTPUT_DIR:-$SCRATCH/datasets/TAIX-Ray}"

ARGS=(
    --output-dir "$OUTPUT_DIR"
    --subsets ${TAIX_RAY_SUBSETS:-data}
    --batch-size "${TAIX_RAY_BATCH_SIZE:-256}"
    --download-workers "${TAIX_RAY_DOWNLOAD_WORKERS:-1}"
)

if [ -n "${TAIX_RAY_IMAGE_COLUMN:-}" ]; then
    ARGS+=(--image-column "$TAIX_RAY_IMAGE_COLUMN")
fi
if [ -n "${TAIX_RAY_SKIP_DOWNLOAD:-}" ]; then
    ARGS+=(--skip-download)
fi
if [ -n "${TAIX_RAY_NO_PREPARE:-}" ]; then
    ARGS+=(--no-prepare)
fi
if [ -n "${TAIX_RAY_OVERWRITE:-}" ]; then
    ARGS+=(--overwrite)
fi

python3 "$DATATHON_DIR/scripts/download_prepare_taix_ray.py" "${ARGS[@]}"
