#!/bin/bash
#SBATCH --job-name=cxr_es_upload
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=08:00:00
#SBATCH --output=cxr_es_upload_%j.log
#SBATCH --error=cxr_es_upload_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
SOURCE_DIR="${CXR_ES_SOURCE_DIR:-$SCRATCH/datasets/datatondatasets/MIMIC-CXR}"
OUTPUT_DIR="${CXR_ES_OUTPUT_DIR:-$SCRATCH/datasets/hf_upload/cxr-report-es-challenge}"
REPO_ID="${CXR_ES_REPO_ID:-dsrestrepo/cxr-report-es-challenge}"

ARGS=(
    --source-dir "$SOURCE_DIR"
    --output-dir "$OUTPUT_DIR"
    --repo-id "$REPO_ID"
    --overwrite
)

if [ -n "${CXR_ES_NO_ARCHIVE_IMAGES:-}" ]; then
    ARGS+=(--no-archive-images)
fi
if [ -n "${CXR_ES_UPLOAD:-}" ]; then
    ARGS+=(--upload)
fi
if [ -n "${CXR_ES_PUBLIC:-}" ]; then
    ARGS+=(--no-private)
fi
if [ -n "${HF_TOKEN:-}" ]; then
    ARGS+=(--token "$HF_TOKEN")
fi

python3 "$DATATHON_DIR/scripts/build_cxr_report_es_challenge_upload.py" "${ARGS[@]}"
