#!/usr/bin/env python3
"""Compare a local clean dataset folder with its Hugging Face dataset repo."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

from huggingface_hub import HfApi


DATASETS = {
    "mimic": ("MIMIC-CXR", "dsrestrepo/mimic-cxr-datathon"),
    "mbrset": ("mBRSET", "dsrestrepo/mbrset-datathon"),
    "cbis": ("CBIS-DDSM-clean", "dsrestrepo/cbis-ddsm-datathon"),
    "lidc224": ("LIDC-IDRI-clean-224", "dsrestrepo/lidc-idri-datathon-224"),
    "lidc384": ("LIDC-IDRI-clean-384", "dsrestrepo/lidc-idri-datathon-384"),
}

IGNORED_PARTS = {
    ".cache",
    ".git",
    ".huggingface",
    "__pycache__",
}


def iter_local_files(folder: Path) -> set[str]:
    paths: set[str] = set()
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(folder)
        if any(part in IGNORED_PARTS for part in rel.parts):
            continue
        paths.add(rel.as_posix())
    return paths


def write_list(path: Path, values: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["path"])
        for value in values:
            writer.writerow([value])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datasets-root",
        default=None,
        help="Folder containing the clean dataset folders. Defaults to $SCRATCH/datasets/datatondatasets.",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=sorted(DATASETS),
        help="Dataset key to audit.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional folder where missing/extra CSV reports will be written.",
    )
    args = parser.parse_args()

    datasets_root = args.datasets_root
    if datasets_root is None and os.environ.get("SCRATCH"):
        datasets_root = str(Path(os.environ["SCRATCH"]) / "datasets" / "datatondatasets")
    if datasets_root is None:
        raise SystemExit("Pass --datasets-root, for example $SCRATCH/datasets/datatondatasets")

    local_name, repo_id = DATASETS[args.dataset]
    local_dir = Path(datasets_root) / local_name
    if not local_dir.is_dir():
        raise SystemExit(f"Missing local dataset folder: {local_dir}")

    print(f"Auditing {args.dataset}")
    print(f"  local: {local_dir}")
    print(f"  repo:  {repo_id}")

    local_files = iter_local_files(local_dir)
    remote_files = set(HfApi().list_repo_files(repo_id=repo_id, repo_type="dataset"))

    missing_remote = sorted(local_files - remote_files)
    extra_remote = sorted(remote_files - local_files)
    matched = len(local_files & remote_files)

    print()
    print(f"Local files:       {len(local_files):,}")
    print(f"Remote files:      {len(remote_files):,}")
    print(f"Matched files:     {matched:,}")
    print(f"Missing on remote: {len(missing_remote):,}")
    print(f"Extra on remote:   {len(extra_remote):,}")

    if missing_remote[:10]:
        print()
        print("First missing remote files:")
        for path in missing_remote[:10]:
            print(f"  {path}")

    if args.output_dir:
        output_dir = Path(args.output_dir)
        write_list(output_dir / f"{args.dataset}_missing_remote.csv", missing_remote)
        write_list(output_dir / f"{args.dataset}_extra_remote.csv", extra_remote)
        print()
        print(f"Wrote audit CSVs to: {output_dir}")


if __name__ == "__main__":
    main()
