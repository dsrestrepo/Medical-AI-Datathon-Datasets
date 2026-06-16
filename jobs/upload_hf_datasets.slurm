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

upload_one() {
    local name="$1"
    local repo_id="$2"
    local local_dir="$3"

    if [ ! -d "$local_dir" ]; then
        echo "Missing local dataset folder for $name: $local_dir"
        exit 1
    fi

    echo "Uploading $name"
    echo "  local: $local_dir"
    echo "  repo:  $repo_id"
    hf upload-large-folder "$repo_id" "$local_dir" --repo-type dataset
}

case "${HF_DATASET:-all}" in
    all)
        upload_one "MIMIC-CXR" "dsrestrepo/mimic-cxr-datathon" "$DATASETS_ROOT/MIMIC-CXR"
        upload_one "mBRSET" "dsrestrepo/mbrset-datathon" "$DATASETS_ROOT/mBRSET"
        upload_one "CBIS-DDSM" "dsrestrepo/cbis-ddsm-datathon" "$DATASETS_ROOT/CBIS-DDSM-clean"
        upload_one "LIDC-IDRI 224" "dsrestrepo/lidc-idri-datathon-224" "$DATASETS_ROOT/LIDC-IDRI-clean-224"
        upload_one "LIDC-IDRI 384" "dsrestrepo/lidc-idri-datathon-384" "$DATASETS_ROOT/LIDC-IDRI-clean-384"
        ;;
    mimic)
        upload_one "MIMIC-CXR" "dsrestrepo/mimic-cxr-datathon" "$DATASETS_ROOT/MIMIC-CXR"
        ;;
    mbrset)
        upload_one "mBRSET" "dsrestrepo/mbrset-datathon" "$DATASETS_ROOT/mBRSET"
        ;;
    cbis)
        upload_one "CBIS-DDSM" "dsrestrepo/cbis-ddsm-datathon" "$DATASETS_ROOT/CBIS-DDSM-clean"
        ;;
    lidc224)
        upload_one "LIDC-IDRI 224" "dsrestrepo/lidc-idri-datathon-224" "$DATASETS_ROOT/LIDC-IDRI-clean-224"
        ;;
    lidc384)
        upload_one "LIDC-IDRI 384" "dsrestrepo/lidc-idri-datathon-384" "$DATASETS_ROOT/LIDC-IDRI-clean-384"
        ;;
    *)
        echo "Unknown HF_DATASET='${HF_DATASET}'"
        echo "Use one of: all, mimic, mbrset, cbis, lidc224, lidc384"
        exit 1
        ;;
esac
