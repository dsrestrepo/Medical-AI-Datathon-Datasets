#!/bin/bash
#SBATCH --job-name=download_cbis
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=download_cbis_%j.log
#SBATCH --error=download_cbis_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
OUTPUT="$SCRATCH/datasets/datatondatasets/CBIS-DDSM"

python3 "$DATATHON_DIR/scripts/download_tcia_collection.py" \
    --collection "CBIS-DDSM" \
    --modality "MG" \
    --output "$OUTPUT" \
    --workers "${SLURM_CPUS_PER_TASK:-4}"

python3 "$DATATHON_DIR/scripts/download_cbis_ddsm_labels.py" \
    --output "$OUTPUT"
