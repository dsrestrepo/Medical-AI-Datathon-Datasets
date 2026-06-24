#!/bin/bash
#SBATCH --job-name=mimic_report_es
#SBATCH --account=dtn@cpu
#SBATCH --partition=compil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=20:00:00
#SBATCH --signal=B:TERM@300
#SBATCH --output=mimic_report_es_%j.log
#SBATCH --error=mimic_report_es_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

DATATHON_DIR="${DATATHON_DIR:-$WORK/datathon}"
MIMIC_DIR="${MIMIC_TRANSLATE_DIR:-$SCRATCH/datasets/datatondatasets/MIMIC-CXR}"
SPLIT="${MIMIC_TRANSLATE_SPLIT:-test}"
INPUT_CSV="${MIMIC_TRANSLATE_INPUT_CSV:-$MIMIC_DIR/$SPLIT.csv}"
OUTPUT_CSV="${MIMIC_TRANSLATE_OUTPUT_CSV:-$MIMIC_DIR/${SPLIT}_spanish.csv}"
ENV_FILE="${MIMIC_TRANSLATE_ENV_FILE:-$DATATHON_DIR/.env}"
CACHE_FILE="${MIMIC_TRANSLATE_CACHE_FILE:-$OUTPUT_CSV.translation_cache.jsonl}"

ARGS=(
    --input-csv "$INPUT_CSV"
    --output-csv "$OUTPUT_CSV"
    --env-file "$ENV_FILE"
    --api-key-env "${MIMIC_TRANSLATE_API_KEY_ENV:-OPENAI_KEY}"
    --model "${MIMIC_TRANSLATE_MODEL:-gpt-5-mini}"
    --workers "${MIMIC_TRANSLATE_WORKERS:-8}"
    --cache-file "$CACHE_FILE"
    --checkpoint-every "${MIMIC_TRANSLATE_CHECKPOINT_EVERY:-25}"
)

if [ -n "${MIMIC_TRANSLATE_MAX_ROWS:-}" ]; then
    ARGS+=(--max-rows "$MIMIC_TRANSLATE_MAX_ROWS")
fi
if [ -n "${MIMIC_TRANSLATE_DRY_RUN:-}" ]; then
    ARGS+=(--dry-run)
fi

python3 "$DATATHON_DIR/scripts/translate_mimic_reports_openai.py" "${ARGS[@]}"
