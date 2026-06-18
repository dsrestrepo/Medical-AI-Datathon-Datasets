#!/usr/bin/env python3
"""Download Medical AI Datathon datasets from Hugging Face."""

from __future__ import annotations

import argparse
from pathlib import Path
import tarfile

from huggingface_hub import snapshot_download


DATASETS = {
    "mimic": {
        "repo_id": "dsrestrepo/mimic-cxr-datathon",
        "folder": "MIMIC-CXR",
    },
    "mbrset": {
        "repo_id": "dsrestrepo/mbrset-datathon",
        "folder": "mBRSET",
    },
    "mbrset224": {
        "repo_id": "dsrestrepo/mbrset-datathon-224",
        "folder": "mBRSET-224",
    },
    "cbis": {
        "repo_id": "dsrestrepo/cbis-ddsm-datathon",
        "folder": "CBIS-DDSM-clean",
    },
    "cbis224": {
        "repo_id": "dsrestrepo/cbis-ddsm-datathon-224",
        "folder": "CBIS-DDSM-clean-224",
    },
    "lidc224": {
        "repo_id": "dsrestrepo/lidc-idri-datathon-224",
        "folder": "LIDC-IDRI-clean-224",
    },
    "lidc384": {
        "repo_id": "dsrestrepo/lidc-idri-datathon-384",
        "folder": "LIDC-IDRI-clean-384",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download one or more gated Medical AI Datathon datasets from "
            "Hugging Face into a local folder."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Local directory where dataset folders will be created.",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["all"],
        choices=["all", *DATASETS.keys()],
        help="Datasets to download. Use 'all' for every dataset.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            "Optional Hugging Face token. If omitted, the script uses the token "
            "from `hf auth login` or the HF_TOKEN environment variable."
        ),
    )
    parser.add_argument(
        "--no-extract-images",
        action="store_true",
        help="Do not extract images.tar.gz after download.",
    )
    return parser.parse_args()


def selected_dataset_keys(requested: list[str]) -> list[str]:
    if "all" in requested:
        return list(DATASETS)
    return requested


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for key in selected_dataset_keys(args.datasets):
        info = DATASETS[key]
        local_dir = output_dir / info["folder"]
        print(f"Downloading {key}: {info['repo_id']} -> {local_dir}", flush=True)
        snapshot_download(
            repo_id=info["repo_id"],
            repo_type="dataset",
            local_dir=local_dir,
            token=args.token,
        )
        if not args.no_extract_images:
            extract_images_archive(local_dir)

    print(f"Done. Datasets are available under: {output_dir}", flush=True)


def extract_images_archive(dataset_dir: Path) -> None:
    archive_path = dataset_dir / "images.tar.gz"
    if not archive_path.is_file():
        return

    images_dir = dataset_dir / "images"
    images_dir.mkdir(exist_ok=True)
    dataset_root = dataset_dir.resolve()

    print(f"Extracting {archive_path}", flush=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            target = (dataset_dir / member.name).resolve()
            if not str(target).startswith(str(dataset_root)):
                raise RuntimeError(f"Unsafe path in image archive: {member.name}")
            tar.extract(member, dataset_dir)


if __name__ == "__main__":
    main()
