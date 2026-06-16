#!/bin/bash
#SBATCH --job-name=prepare_cbis
#SBATCH --account=dtn@cpu
#SBATCH --partition=prepost
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --hint=nomultithread
#SBATCH --time=04:00:00
#SBATCH --output=prepare_cbis_%j.log
#SBATCH --error=prepare_cbis_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
SOURCE="$SCRATCH/datasets/datatondatasets/CBIS-DDSM"
OUTPUT="$SCRATCH/datasets/datatondatasets/CBIS-DDSM-clean"

python3 "$DATATHON_DIR/scripts/prepare_cbis_ddsm.py" \
    --source "$SOURCE" \
    --output "$OUTPUT" \
    --size "${CBIS_IMAGE_SIZE:-224}" \
    ${CBIS_OVERWRITE:+--overwrite}

