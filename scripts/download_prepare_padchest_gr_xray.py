#!/usr/bin/env python3
"""Download and prepare the PadChest-GR-Xray Hugging Face dataset.

The Hugging Face repository stores the data as parquet shards under
`data/{train,valid,test}`. This script downloads those shards into
`$SCRATCH/datasets/PadChest-GR-Xray/raw` by default and can also materialize
embedded image bytes into a simple folder layout:

    prepared/
    ├── images/
    │   ├── train/
    │   ├── valid/
    │   └── test/
    ├── train.csv
    ├── valid.csv
    └── test.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download

try:
    import pyarrow.parquet as pq
except ImportError as error:
    raise RuntimeError(
        "This script requires pyarrow to read parquet files. Install it with "
        "`pip install pyarrow` or add it to the datathon environment."
    ) from error


REPO_ID = "JasonZZ0601/PadChest-GR-Xray"
SPLITS = ("train", "valid", "test")
IMAGE_COLUMN_CANDIDATES = (
    "image",
    "xray",
    "x_ray",
    "radiograph",
    "jpg",
    "png",
)


def parse_args() -> argparse.Namespace:
    scratch = os.environ.get("SCRATCH")
    default_output = (
        Path(scratch) / "datasets" / "PadChest-GR-Xray" if scratch else None
    )

    parser = argparse.ArgumentParser(
        description=(
            "Download JasonZZ0601/PadChest-GR-Xray parquet shards from Hugging "
            "Face and prepare image folders plus metadata CSV files."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output,
        help=(
            "Dataset root. Defaults to $SCRATCH/datasets/PadChest-GR-Xray. "
            "Required if SCRATCH is not set."
        ),
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Where to store downloaded parquet files. Defaults to OUTPUT/raw.",
    )
    parser.add_argument(
        "--prepared-dir",
        type=Path,
        default=None,
        help="Where to write prepared images and CSVs. Defaults to OUTPUT/prepared.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=list(SPLITS),
        choices=SPLITS,
        help="Dataset splits to download and prepare.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            "Optional Hugging Face token. If omitted, uses `hf auth login` or "
            "the HF_TOKEN environment variable."
        ),
    )
    parser.add_argument(
        "--image-column",
        default=None,
        help="Name of the parquet column containing image data. Auto-detected by default.",
    )
    parser.add_argument(
        "--no-prepare",
        action="store_true",
        help="Only download the parquet shards; do not extract images or write CSVs.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse an existing raw parquet snapshot and only run the preparation step.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing prepared image files and CSV files.",
    )
    return parser.parse_args()


def resolve_dirs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.output_dir is None and (args.raw_dir is None or args.prepared_dir is None):
        raise ValueError(
            "--output-dir is required when SCRATCH is not set unless both "
            "--raw-dir and --prepared-dir are provided"
        )

    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else Path()
    raw_dir = (
        args.raw_dir.expanduser().resolve()
        if args.raw_dir
        else (output_dir / "raw").resolve()
    )
    prepared_dir = (
        args.prepared_dir.expanduser().resolve()
        if args.prepared_dir
        else (output_dir / "prepared").resolve()
    )
    return output_dir, raw_dir, prepared_dir


def download_parquet_shards(raw_dir: Path, splits: list[str], token: str | None) -> None:
    allow_patterns = [f"data/{split}/*.parquet" for split in splits]
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {REPO_ID} parquet shards to {raw_dir}", flush=True)
    snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        local_dir=raw_dir,
        allow_patterns=allow_patterns,
        token=token,
    )


def split_parquet_files(raw_dir: Path, split: str) -> list[Path]:
    split_dir = raw_dir / "data" / split
    files = sorted(split_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for split '{split}' in {split_dir}")
    return files


def choose_image_column(columns: list[str], requested: str | None) -> str:
    if requested is not None:
        if requested not in columns:
            raise ValueError(
                f"Requested image column '{requested}' not found. Columns: {columns}"
            )
        return requested

    for name in IMAGE_COLUMN_CANDIDATES:
        if name in columns:
            return name

    raise ValueError(
        "Could not auto-detect an image column. Use --image-column. "
        f"Available columns: {columns}"
    )


def image_payload(value: Any) -> tuple[bytes | None, str | None]:
    """Return embedded bytes and an optional source path from common HF image shapes."""
    if value is None:
        return None, None

    if isinstance(value, bytes):
        return value, None

    if isinstance(value, dict):
        data = value.get("bytes")
        path = value.get("path")
        if isinstance(data, bytes):
            return data, str(path) if path else None
        if isinstance(path, str):
            return None, path

    if isinstance(value, str):
        return None, value

    return None, None


def image_extension(data: bytes, source_path: str | None) -> str:
    if source_path:
        suffix = Path(source_path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            return ".jpg" if suffix == ".jpeg" else suffix
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def prepare_split(
    raw_dir: Path,
    prepared_dir: Path,
    split: str,
    requested_image_column: str | None,
    overwrite: bool,
) -> int:
    parquet_files = split_parquet_files(raw_dir, split)
    image_dir = prepared_dir / "images" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    csv_path = prepared_dir / f"{split}.csv"
    if csv_path.exists() and not overwrite:
        raise FileExistsError(f"{csv_path} already exists. Pass --overwrite to replace it.")

    image_column: str | None = None
    metadata_columns: list[str] | None = None
    row_count = 0
    missing_images = 0

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] | None = None

        for parquet_path in parquet_files:
            table = pq.read_table(parquet_path)
            columns = table.column_names
            if image_column is None:
                image_column = choose_image_column(columns, requested_image_column)
                metadata_columns = [column for column in columns if column != image_column]
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["image", "split", "source_parquet", *metadata_columns],
                )
                writer.writeheader()

            if image_column not in columns:
                raise ValueError(f"{parquet_path} does not contain column {image_column}")

            assert metadata_columns is not None
            assert writer is not None

            rows = table.to_pylist()
            for row_index, row in enumerate(rows):
                data, source_path = image_payload(row.get(image_column))
                if data is None:
                    missing_images += 1
                    continue

                extension = image_extension(data, source_path)
                image_name = f"{split}_{row_count:07d}{extension}"
                image_path = image_dir / image_name
                if image_path.exists() and not overwrite:
                    raise FileExistsError(
                        f"{image_path} already exists. Pass --overwrite to replace it."
                    )
                image_path.write_bytes(data)

                metadata = {
                    "image": f"images/{split}/{image_name}",
                    "split": split,
                    "source_parquet": f"{parquet_path.name}:{row_index}",
                }
                metadata.update(
                    {column: csv_value(row.get(column)) for column in metadata_columns}
                )
                writer.writerow(metadata)
                row_count += 1

            print(
                f"Prepared {row_count:,} images from {split} "
                f"({parquet_path.name})",
                flush=True,
            )

    if missing_images:
        print(
            f"Warning: skipped {missing_images:,} rows in {split} without embedded image bytes",
            flush=True,
        )

    return row_count


def prepare_dataset(
    raw_dir: Path,
    prepared_dir: Path,
    splits: list[str],
    image_column: str | None,
    overwrite: bool,
) -> None:
    total = 0
    for split in splits:
        count = prepare_split(raw_dir, prepared_dir, split, image_column, overwrite)
        print(f"Finished {split}: {count:,} images", flush=True)
        total += count

    readme = prepared_dir / "README.md"
    if overwrite or not readme.exists():
        readme.write_text(
            "\n".join(
                [
                    "# PadChest-GR-Xray",
                    "",
                    f"Source: https://huggingface.co/datasets/{REPO_ID}",
                    "",
                    "Prepared layout:",
                    "",
                    "```text",
                    "images/{train,valid,test}/",
                    "train.csv",
                    "valid.csv",
                    "test.csv",
                    "```",
                    "",
                    "Each CSV row points to a materialized image via the `image` column.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    print(f"Prepared {total:,} total images under {prepared_dir}", flush=True)


def main() -> None:
    args = parse_args()
    _output_dir, raw_dir, prepared_dir = resolve_dirs(args)

    if not args.skip_download:
        download_parquet_shards(raw_dir, args.splits, args.token)
    if not args.no_prepare:
        prepare_dataset(
            raw_dir=raw_dir,
            prepared_dir=prepared_dir,
            splits=args.splits,
            image_column=args.image_column,
            overwrite=args.overwrite,
        )

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
