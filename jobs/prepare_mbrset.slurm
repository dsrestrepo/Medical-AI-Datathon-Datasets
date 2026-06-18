#!/bin/bash
#SBATCH --job-name=datathon_mbrset
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=datathon_mbrset_%j.log
#SBATCH --error=datathon_mbrset_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
SOURCE="$SCRATCH/datasets/mBRSET/mbrset"
OUTPUT="$SCRATCH/datasets/datatondatasets/mBRSET"

python3 "$DATATHON_DIR/scripts/prepare_mbrset.py" \
    --source "$SOURCE" \
    --output "$OUTPUT" \
    --image-folder "${MBRSET_IMAGE_FOLDER:-images}" \
    --size "${MBRSET_IMAGE_SIZE:-448}" \
    --workers "${SLURM_CPUS_PER_TASK:-8}" \
    ${MBRSET_OVERWRITE:+--overwrite}
