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
    "cbis": {
        "repo_id": "dsrestrepo/cbis-ddsm-datathon",
        "folder": "CBIS-DDSM-clean",
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
        "--no-extract-shards",
        action="store_true",
        help="Do not extract image_shards/*.tar files after download.",
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
        if not args.no_extract_shards:
            extract_image_shards(local_dir)

    print(f"Done. Datasets are available under: {output_dir}", flush=True)


def extract_image_shards(dataset_dir: Path) -> None:
    shards_dir = dataset_dir / "image_shards"
    if not shards_dir.is_dir():
        return

    images_dir = dataset_dir / "images"
    images_dir.mkdir(exist_ok=True)
    dataset_root = dataset_dir.resolve()

    for shard in sorted(shards_dir.glob("*.tar")):
        print(f"Extracting {shard}", flush=True)
        with tarfile.open(shard, "r") as tar:
            for member in tar.getmembers():
                target = (dataset_dir / member.name).resolve()
                if not str(target).startswith(str(dataset_root)):
                    raise RuntimeError(f"Unsafe path in tar shard: {member.name}")
                tar.extract(member, dataset_dir)


if __name__ == "__main__":
    main()
