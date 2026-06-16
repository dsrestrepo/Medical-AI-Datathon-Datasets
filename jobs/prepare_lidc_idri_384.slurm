#!/bin/bash
#SBATCH --job-name=prepare_lidc384
#SBATCH --account=dtn@cpu
#SBATCH --partition=prepost
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --hint=nomultithread
#SBATCH --time=20:00:00
#SBATCH --output=prepare_lidc384_%j.log
#SBATCH --error=prepare_lidc384_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
SOURCE="${LIDC_SOURCE_DIR:-$SCRATCH/datasets/datatondatasets/LIDC-IDRI}"
OUTPUT="${LIDC_OUTPUT_DIR:-$SCRATCH/datasets/datatondatasets/LIDC-IDRI-clean-384}"

python3 "$DATATHON_DIR/scripts/prepare_lidc_idri.py" \
    --source "$SOURCE" \
    --output "$OUTPUT" \
    --size 384 \
    --test-fraction "${LIDC_TEST_FRACTION:-0.2}" \
    --seed "${LIDC_SPLIT_SEED:-2026}" \
    ${LIDC_OVERWRITE:+--overwrite}
