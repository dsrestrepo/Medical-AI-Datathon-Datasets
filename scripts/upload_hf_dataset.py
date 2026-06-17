#!/usr/bin/env python3
"""Upload one clean datathon dataset folder to Hugging Face."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi


DATASETS = {
    "mimic": ("MIMIC-CXR", "dsrestrepo/mimic-cxr-datathon"),
    "mbrset": ("mBRSET", "dsrestrepo/mbrset-datathon"),
    "cbis": ("CBIS-DDSM-clean", "dsrestrepo/cbis-ddsm-datathon"),
    "lidc224": ("LIDC-IDRI-clean-224", "dsrestrepo/lidc-idri-datathon-224"),
    "lidc384": ("LIDC-IDRI-clean-384", "dsrestrepo/lidc-idri-datathon-384"),
}

IGNORE_PATTERNS = [
    ".cache/**",
    ".huggingface/**",
    "__pycache__/**",
    "*.log",
    "*.err",
    "*.tmp",
    "*.part",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datasets-root",
        required=True,
        help="Folder containing the clean dataset folders.",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=sorted(DATASETS),
        help="Dataset key to upload. Upload one dataset per run.",
    )
    parser.add_argument(
        "--mode",
        choices=("folder", "large-folder"),
        default="folder",
        help=(
            "'folder' creates one commit for the whole dataset. "
            "'large-folder' is resumable but may create many commits and hit commit rate limits."
        ),
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=4,
        help="Worker count used only with --mode large-folder.",
    )
    args = parser.parse_args()

    local_name, repo_id = DATASETS[args.dataset]
    local_dir = Path(args.datasets_root) / local_name
    if not local_dir.is_dir():
        raise SystemExit(f"Missing local dataset folder: {local_dir}")

    print(f"Uploading {args.dataset}")
    print(f"  local: {local_dir}")
    print(f"  repo:  {repo_id}")
    print(f"  mode:  {args.mode}")

    api = HfApi()

    if args.mode == "folder":
        commit = api.upload_folder(
            repo_id=repo_id,
            repo_type="dataset",
            folder_path=local_dir,
            commit_message=f"Upload {local_name} dataset",
            ignore_patterns=IGNORE_PATTERNS,
        )
        print(f"Commit URL: {commit.commit_url}")
        return

    api.upload_large_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=local_dir,
        num_workers=args.num_workers,
    )


if __name__ == "__main__":
    main()
