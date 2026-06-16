#!/bin/bash
#SBATCH --job-name=datathon_mimic
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=20:00:00
#SBATCH --output=datathon_mimic_%j.log
#SBATCH --error=datathon_mimic_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
SOURCE="$SCRATCH/datasets/MIMIC/mimic"
OUTPUT="$SCRATCH/datasets/datatondatasets/MIMIC-CXR"

if [ -d "$OUTPUT" ]; then
    echo "Existing clean MIMIC-CXR folder found at $OUTPUT"
    echo "Updating CSVs in place and refreshing README.md"
    python3 "$DATATHON_DIR/scripts/prepare_mimic.py" \
        --source "$SOURCE" \
        --output "$OUTPUT" \
        --clean-existing
else
    python3 "$DATATHON_DIR/scripts/prepare_mimic.py" \
        --source "$SOURCE" \
        --output "$OUTPUT" \
        --workers "${SLURM_CPUS_PER_TASK:-8}"
fi
