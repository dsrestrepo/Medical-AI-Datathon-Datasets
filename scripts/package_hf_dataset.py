#!/usr/bin/env python3
"""Package clean datasets into Hugging Face friendly folders.

The clean local datasets may contain tens or hundreds of thousands of small
image files. Uploading each image as a separate Hub file creates too many commit
operations. This script keeps CSV/readme files as regular files but packs
`images/` into tar shards.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import tarfile
from pathlib import Path


DATASETS = {
    "mimic": "MIMIC-CXR",
    "mbrset": "mBRSET",
    "cbis": "CBIS-DDSM-clean",
    "lidc224": "LIDC-IDRI-clean-224",
    "lidc384": "LIDC-IDRI-clean-384",
}

SKIP_DIRS = {
    ".cache",
    ".git",
    ".huggingface",
    "__pycache__",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datasets-root",
        required=True,
        type=Path,
        help="Folder containing the clean dataset folders.",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
        help="Folder where packaged Hugging Face upload folders will be written.",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["all", *sorted(DATASETS)],
        help="Dataset to package.",
    )
    parser.add_argument(
        "--images-per-shard",
        type=int,
        default=5000,
        help="Maximum number of images per tar shard.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove the existing packaged dataset folder before writing it.",
    )
    return parser.parse_args()


def selected_keys(dataset: str) -> list[str]:
    if dataset == "all":
        return list(DATASETS)
    return [dataset]


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def copy_non_image_content(src: Path, dst: Path) -> None:
    for child in src.iterdir():
        if child.name == "images" or should_skip(child):
            continue

        target = dst / child.name
        if child.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(child, target, ignore=shutil.ignore_patterns(*SKIP_DIRS))
        elif child.is_file():
            shutil.copy2(child, target)


def write_image_shards(src_images: Path, dst: Path, images_per_shard: int) -> None:
    image_files = sorted(path for path in src_images.iterdir() if path.is_file())
    shards_dir = dst / "image_shards"
    shards_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = dst / "image_shards.csv"
    with manifest_path.open("w", newline="") as manifest_file:
        writer = csv.writer(manifest_file)
        writer.writerow(["image", "shard", "path_in_shard"])

        for shard_index, start in enumerate(range(0, len(image_files), images_per_shard)):
            shard_images = image_files[start : start + images_per_shard]
            shard_name = f"images-{shard_index:05d}.tar"
            shard_path = shards_dir / shard_name
            print(f"  writing {shard_path} ({len(shard_images)} images)", flush=True)

            with tarfile.open(shard_path, "w") as tar:
                for image_path in shard_images:
                    path_in_shard = f"images/{image_path.name}"
                    tar.add(image_path, arcname=path_in_shard)
                    writer.writerow([image_path.name, f"image_shards/{shard_name}", path_in_shard])


def package_one(src: Path, dst: Path, images_per_shard: int, overwrite: bool) -> None:
    if not src.is_dir():
        raise SystemExit(f"Missing source dataset folder: {src}")
    if dst.exists():
        if not overwrite:
            raise SystemExit(f"Output folder already exists, use --overwrite: {dst}")
        shutil.rmtree(dst)

    dst.mkdir(parents=True, exist_ok=True)
    copy_non_image_content(src, dst)

    images_dir = src / "images"
    if images_dir.is_dir():
        write_image_shards(images_dir, dst, images_per_shard)
    else:
        print(f"  no images/ folder found; copied dataset without image sharding", flush=True)


def main() -> None:
    args = parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    for key in selected_keys(args.dataset):
        folder = DATASETS[key]
        src = args.datasets_root / folder
        dst = args.output_root / folder
        print(f"Packaging {key}: {src} -> {dst}", flush=True)
        package_one(src, dst, args.images_per_shard, args.overwrite)

    print(f"Done. Packaged datasets are under: {args.output_root}", flush=True)


if __name__ == "__main__":
    main()
