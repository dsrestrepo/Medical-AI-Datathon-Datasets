#!/usr/bin/env python3
"""Build and optionally upload the CXR Report ES Challenge dataset folder."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import tarfile
from pathlib import Path

from dataset_utils import read_datathon_readme


SPLITS = ("train", "valid", "test")
DEFAULT_REPO_ID = "dsrestrepo/cxr-report-es-challenge"


def parse_args() -> argparse.Namespace:
    scratch = os.environ.get("SCRATCH")
    default_source = (
        Path(scratch) / "datasets" / "datatondatasets" / "MIMIC-CXR"
        if scratch
        else None
    )
    default_output = (
        Path(scratch) / "datasets" / "hf_upload" / "cxr-report-es-challenge"
        if scratch
        else Path("cxr-report-es-challenge-upload")
    )

    parser = argparse.ArgumentParser(
        description=(
            "Build a Hugging Face upload folder with train/valid/test CSVs "
            "that include report_spanish and a compressed images.tar.gz."
        )
    )
    parser.add_argument("--source-dir", type=Path, default=default_source)
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--splits", nargs="+", default=list(SPLITS), choices=SPLITS)
    parser.add_argument("--spanish-suffix", default="_spanish")
    parser.add_argument("--translated-column", default="report_spanish")
    parser.add_argument("--archive-images", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--private", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--token", default=None)
    return parser.parse_args()


def translated_csv_path(source_dir: Path, split: str, suffix: str) -> Path:
    return source_dir / f"{split}{suffix}.csv"


def read_translations(
    path: Path,
    translated_column: str,
) -> dict[tuple[str, str, str], str]:
    translations: dict[tuple[str, str, str], str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"image", "subject_id", "study_id", translated_column}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError(f"{path} must contain columns: {sorted(required)}")

        for row_number, row in enumerate(reader, start=2):
            key = (row["image"], row["subject_id"], row["study_id"])
            translation = row.get(translated_column, "").strip()
            if not translation:
                raise ValueError(f"Missing {translated_column} in {path}, row {row_number}")
            previous = translations.get(key)
            if previous is not None and previous != translation:
                raise ValueError(f"Conflicting translation for {key} in {path}")
            translations[key] = translation

    return translations


def merge_split(
    source_csv: Path,
    translated_csv: Path,
    output_csv: Path,
    translated_column: str,
) -> int:
    translations = read_translations(translated_csv, translated_column)
    rows_written = 0

    with source_csv.open("r", encoding="utf-8", newline="") as source_handle:
        reader = csv.DictReader(source_handle)
        required = {"image", "subject_id", "study_id", "report"}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError(f"{source_csv} must contain columns: {sorted(required)}")

        output_fields = list(reader.fieldnames)
        if translated_column not in output_fields:
            output_fields.insert(output_fields.index("report") + 1, translated_column)

        with output_csv.open("w", encoding="utf-8", newline="") as output_handle:
            writer = csv.DictWriter(output_handle, fieldnames=output_fields)
            writer.writeheader()

            for row_number, row in enumerate(reader, start=2):
                key = (row["image"], row["subject_id"], row["study_id"])
                translation = translations.get(key)
                if not translation:
                    raise ValueError(
                        f"No Spanish translation for {key} from {source_csv}, row {row_number}"
                    )
                output_row = {field: row.get(field, "") for field in output_fields}
                output_row[translated_column] = translation
                writer.writerow(output_row)
                rows_written += 1

    if rows_written != len(translations):
        raise ValueError(
            f"{translated_csv} has {len(translations):,} translations but "
            f"{source_csv} matched {rows_written:,} rows"
        )

    return rows_written


def add_images_archive(source_images: Path, output_archive: Path) -> None:
    if not source_images.is_dir():
        raise FileNotFoundError(f"Missing images directory: {source_images}")
    with tarfile.open(output_archive, "w:gz") as tar:
        tar.add(source_images, arcname="images")


def copy_images(source_images: Path, output_images: Path) -> None:
    if output_images.exists():
        shutil.rmtree(output_images)
    shutil.copytree(source_images, output_images)


def upload_folder(output_dir: Path, repo_id: str, private: bool, token: str | None) -> None:
    try:
        from huggingface_hub import HfApi
    except ImportError as error:
        raise RuntimeError(
            "Uploading requires huggingface_hub. Install it or use the datathon env."
        ) from error

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=output_dir,
        commit_message="Upload CXR Report ES Challenge dataset",
    )


def main() -> None:
    args = parse_args()
    if args.source_dir is None:
        raise ValueError("--source-dir is required when SCRATCH is not set")

    source_dir = args.source_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if output_dir.exists():
        if not args.overwrite:
            raise FileExistsError(f"{output_dir} already exists. Pass --overwrite.")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for split in args.splits:
        source_csv = source_dir / f"{split}.csv"
        spanish_csv = translated_csv_path(source_dir, split, args.spanish_suffix)
        if not source_csv.is_file():
            raise FileNotFoundError(f"Missing source split: {source_csv}")
        if not spanish_csv.is_file():
            raise FileNotFoundError(f"Missing translated split: {spanish_csv}")

        rows = merge_split(
            source_csv=source_csv,
            translated_csv=spanish_csv,
            output_csv=output_dir / f"{split}.csv",
            translated_column=args.translated_column,
        )
        print(f"Wrote {split}.csv: {rows:,} rows", flush=True)

    (output_dir / "README.md").write_text(
        read_datathon_readme("CXR-REPORT-ES-CHALLENGE.md"),
        encoding="utf-8",
    )

    source_images = source_dir / "images"
    if args.archive_images:
        add_images_archive(source_images, output_dir / "images.tar.gz")
        print(f"Wrote {output_dir / 'images.tar.gz'}", flush=True)
    else:
        copy_images(source_images, output_dir / "images")
        print(f"Copied images to {output_dir / 'images'}", flush=True)

    if args.upload:
        upload_folder(
            output_dir=output_dir,
            repo_id=args.repo_id,
            private=args.private,
            token=args.token,
        )
        print(f"Uploaded {output_dir} to https://huggingface.co/datasets/{args.repo_id}", flush=True)

    print(f"Done. Upload folder: {output_dir}", flush=True)


if __name__ == "__main__":
    main()
