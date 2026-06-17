#!/bin/bash
#SBATCH --job-name=upload_hf_data
#SBATCH --account=dtn@cpu
#SBATCH --partition=prepost
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --time=20:00:00
#SBATCH --output=upload_hf_data_%j.log
#SBATCH --error=upload_hf_data_%j.err

set -euo pipefail

: "${WORK:?WORK is not set}"
: "${SCRATCH:?SCRATCH is not set}"

module purge
module load miniforge/24.9.0

eval "$(conda shell.bash hook)"
export CONDA_ENVS_PATH="$WORK/.conda/envs"
conda activate "${DATATHON_CONDA_ENV:-llms}"

if ! command -v hf >/dev/null 2>&1; then
    echo "The Hugging Face CLI command 'hf' was not found in this environment."
    echo "Install it once with: pip install -U huggingface_hub"
    exit 1
fi

if ! hf auth whoami >/dev/null 2>&1; then
    echo "Hugging Face authentication is not configured."
    echo "Run 'hf auth login' once, or submit this job with HF_TOKEN set."
    exit 1
fi

DATASETS_ROOT="${DATASETS_ROOT:-$SCRATCH/datasets/datatondatasets}"
: "${HF_DATASET:?Set HF_DATASET to one of: mimic, mbrset, cbis, lidc224, lidc384}"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}/scripts"
if [ ! -f "$SCRIPT_DIR/upload_hf_dataset.py" ]; then
    echo "Could not find $SCRIPT_DIR/upload_hf_dataset.py"
    echo "Submit this job from the datathon repository root."
    exit 1
fi

export HF_XET_HIGH_PERFORMANCE="${HF_XET_HIGH_PERFORMANCE:-1}"
export HF_HOME="${HF_HOME:-$WORK/.cache/huggingface}"

upload_one() {
    local name="$1"
    local key="$2"
    local local_dir="$3"

    if [ ! -d "$local_dir" ]; then
        echo "Missing local dataset folder for $name: $local_dir"
        exit 1
    fi

    echo "Uploading $name"
    echo "  local: $local_dir"
    echo "  key:   $key"
    echo "  mode:  ${HF_UPLOAD_MODE:-folder}"
    python "$SCRIPT_DIR/upload_hf_dataset.py" \
        --datasets-root "$DATASETS_ROOT" \
        --dataset "$key" \
        --mode "${HF_UPLOAD_MODE:-folder}" \
        --num-workers "${HF_NUM_WORKERS:-4}"
}

case "$HF_DATASET" in
    mimic)
        upload_one "MIMIC-CXR" "mimic" "$DATASETS_ROOT/MIMIC-CXR"
        ;;
    mbrset)
        upload_one "mBRSET" "mbrset" "$DATASETS_ROOT/mBRSET"
        ;;
    cbis)
        upload_one "CBIS-DDSM" "cbis" "$DATASETS_ROOT/CBIS-DDSM-clean"
        ;;
    lidc224)
        upload_one "LIDC-IDRI 224" "lidc224" "$DATASETS_ROOT/LIDC-IDRI-clean-224"
        ;;
    lidc384)
        upload_one "LIDC-IDRI 384" "lidc384" "$DATASETS_ROOT/LIDC-IDRI-clean-384"
        ;;
    *)
        echo "Unknown HF_DATASET='${HF_DATASET}'"
        echo "Use one of: mimic, mbrset, cbis, lidc224, lidc384"
        exit 1
        ;;
esac
