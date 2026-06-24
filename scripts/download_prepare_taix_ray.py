#!/usr/bin/env python3
"""Download and prepare the TLAIM/TAIX-Ray Hugging Face dataset."""

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
        "download_prepare_taix_ray.py requires pyarrow to read parquet files."
    ) from error


REPO_ID = "TLAIM/TAIX-Ray"
SUBSETS = ("data", "original")
DEFAULT_SUBSETS = ("data",)
IMAGE_COLUMN_CANDIDATES = (
    "Image",
    "image",
    "xray",
    "x_ray",
    "radiograph",
    "jpg",
    "png",
)


def parse_args() -> argparse.Namespace:
    scratch = os.environ.get("SCRATCH")
    default_output = Path(scratch) / "datasets" / "TAIX-Ray" if scratch else None

    parser = argparse.ArgumentParser(
        description=(
            "Download TLAIM/TAIX-Ray parquet shards from Hugging Face and "
            "prepare image folders plus CSV metadata."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output,
        help=(
            "Dataset root. Defaults to $SCRATCH/datasets/TAIX-Ray. Required "
            "if SCRATCH is not set unless --raw-dir and --prepared-dir are used."
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
        "--subsets",
        nargs="+",
        default=list(DEFAULT_SUBSETS),
        choices=SUBSETS,
        help=(
            "Top-level parquet folders to download and prepare. Defaults to "
            "'data' (the 512px/default configuration). Add 'original' only "
            "when you need the 1.2TB variable-size images."
        ),
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
        "--batch-size",
        type=int,
        default=256,
        help="Rows to decode at a time from each parquet file.",
    )
    parser.add_argument(
        "--download-workers",
        type=int,
        default=1,
        help="Parallel Hugging Face download workers. Use 1 on restrictive proxies.",
    )
    parser.add_argument(
        "--no-prepare",
        action="store_true",
        help="Only download parquet shards; do not extract images or write CSVs.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse an existing raw parquet snapshot and only run preparation.",
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


def download_parquet_shards(
    raw_dir: Path,
    subsets: list[str],
    token: str | None,
    download_workers: int,
) -> None:
    if download_workers < 1:
        raise ValueError("--download-workers must be at least 1")

    allow_patterns = [f"{subset}/*.parquet" for subset in subsets]
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {REPO_ID} parquet shards to {raw_dir}", flush=True)
    snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        local_dir=raw_dir,
        allow_patterns=allow_patterns,
        max_workers=download_workers,
        token=token,
    )


def subset_parquet_files(raw_dir: Path, subset: str) -> list[Path]:
    subset_dir = raw_dir / subset
    files = sorted(subset_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for subset '{subset}' in {subset_dir}")
    return files


def choose_image_column(columns: list[str], requested: str | None) -> str:
    if requested is not None:
        if requested not in columns:
            raise ValueError(
                f"Requested image column '{requested}' not found. Columns: {columns}"
            )
        return requested

    for column in IMAGE_COLUMN_CANDIDATES:
        if column in columns:
            return column

    raise ValueError(
        "Could not auto-detect an image column. Use --image-column. "
        f"Available columns: {columns}"
    )


def image_payload(value: Any) -> tuple[bytes | None, str | None]:
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


def prepare_subset(
    raw_dir: Path,
    prepared_dir: Path,
    subset: str,
    requested_image_column: str | None,
    batch_size: int,
    overwrite: bool,
) -> int:
    parquet_files = subset_parquet_files(raw_dir, subset)
    image_dir = prepared_dir / "images" / subset
    image_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    csv_path = prepared_dir / f"{subset}.csv"
    if csv_path.exists() and not overwrite:
        raise FileExistsError(f"{csv_path} already exists. Pass --overwrite to replace it.")

    image_column: str | None = None
    metadata_columns: list[str] | None = None
    row_count = 0
    missing_images = 0

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] | None = None

        for parquet_path in parquet_files:
            parquet_file = pq.ParquetFile(parquet_path)
            columns = parquet_file.schema_arrow.names
            if image_column is None:
                image_column = choose_image_column(columns, requested_image_column)
                metadata_columns = [column for column in columns if column != image_column]
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["image", "subset", "source_parquet", *metadata_columns],
                )
                writer.writeheader()

            if image_column not in columns:
                raise ValueError(f"{parquet_path} does not contain column {image_column}")

            assert metadata_columns is not None
            assert writer is not None

            parquet_row_offset = 0
            for batch in parquet_file.iter_batches(batch_size=batch_size):
                rows = batch.to_pylist()
                for batch_row_index, row in enumerate(rows):
                    data, source_path = image_payload(row.get(image_column))
                    if data is None:
                        missing_images += 1
                        continue

                    extension = image_extension(data, source_path)
                    image_name = f"{subset}_{row_count:08d}{extension}"
                    image_path = image_dir / image_name
                    if image_path.exists() and not overwrite:
                        raise FileExistsError(
                            f"{image_path} already exists. Pass --overwrite to replace it."
                        )
                    image_path.write_bytes(data)

                    source_row = parquet_row_offset + batch_row_index
                    metadata = {
                        "image": f"images/{subset}/{image_name}",
                        "subset": subset,
                        "source_parquet": f"{parquet_path.name}:{source_row}",
                    }
                    metadata.update(
                        {column: csv_value(row.get(column)) for column in metadata_columns}
                    )
                    writer.writerow(metadata)
                    row_count += 1

                parquet_row_offset += len(rows)

            print(
                f"Prepared {row_count:,} images from {subset} ({parquet_path.name})",
                flush=True,
            )

    if missing_images:
        print(
            f"Warning: skipped {missing_images:,} rows in {subset} without embedded image bytes",
            flush=True,
        )
    return row_count


def prepare_dataset(
    raw_dir: Path,
    prepared_dir: Path,
    subsets: list[str],
    image_column: str | None,
    batch_size: int,
    overwrite: bool,
) -> None:
    if batch_size < 1:
        raise ValueError("--batch-size must be at least 1")

    total = 0
    for subset in subsets:
        count = prepare_subset(
            raw_dir=raw_dir,
            prepared_dir=prepared_dir,
            subset=subset,
            requested_image_column=image_column,
            batch_size=batch_size,
            overwrite=overwrite,
        )
        print(f"Finished {subset}: {count:,} images", flush=True)
        total += count

    readme = prepared_dir / "README.md"
    if overwrite or not readme.exists():
        readme.write_text(
            "\n".join(
                [
                    "# TAIX-Ray",
                    "",
                    f"Source: https://huggingface.co/datasets/{REPO_ID}",
                    "",
                    "Prepared layout:",
                    "",
                    "```text",
                    "images/data/",
                    "images/original/  # only when --subsets original is used",
                    "data.csv",
                    "original.csv",
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
        download_parquet_shards(
            raw_dir=raw_dir,
            subsets=args.subsets,
            token=args.token,
            download_workers=args.download_workers,
        )
    if not args.no_prepare:
        prepare_dataset(
            raw_dir=raw_dir,
            prepared_dir=prepared_dir,
            subsets=args.subsets,
            image_column=args.image_column,
            batch_size=args.batch_size,
            overwrite=args.overwrite,
        )

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
