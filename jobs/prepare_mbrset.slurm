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

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
SOURCE="$SCRATCH/datasets/mBRSET/mbrset"
OUTPUT="$SCRATCH/datasets/datatondatasets/mBRSET"

python3 "$DATATHON_DIR/scripts/prepare_mbrset.py" \
    --source "$SOURCE" \
    --output "$OUTPUT" \
    --workers "${SLURM_CPUS_PER_TASK:-8}"

