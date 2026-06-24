#!/bin/bash
#SBATCH --job-name=padchest_gr_xray
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=12:00:00
#SBATCH --output=padchest_gr_xray_%j.log
#SBATCH --error=padchest_gr_xray_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
OUTPUT_DIR="${PADCHEST_GR_XRAY_OUTPUT_DIR:-$SCRATCH/datasets/PadChest-GR-Xray}"

ARGS=(
    --output-dir "$OUTPUT_DIR"
    --splits ${PADCHEST_GR_XRAY_SPLITS:-train valid test}
)

if [ -n "${PADCHEST_GR_XRAY_IMAGE_COLUMN:-}" ]; then
    ARGS+=(--image-column "$PADCHEST_GR_XRAY_IMAGE_COLUMN")
fi
if [ -n "${PADCHEST_GR_XRAY_SKIP_DOWNLOAD:-}" ]; then
    ARGS+=(--skip-download)
fi
if [ -n "${PADCHEST_GR_XRAY_NO_PREPARE:-}" ]; then
    ARGS+=(--no-prepare)
fi
if [ -n "${PADCHEST_GR_XRAY_OVERWRITE:-}" ]; then
    ARGS+=(--overwrite)
fi

python3 "$DATATHON_DIR/scripts/download_prepare_padchest_gr_xray.py" "${ARGS[@]}"
