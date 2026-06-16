#!/usr/bin/env python3
"""Download and normalize official CBIS-DDSM label CSVs."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_URLS = {
    "mass_train": "https://wiki.cancerimagingarchive.net/download/attachments/22516629/mass_case_description_train_set.csv?api=v2",
    "mass_test": "https://wiki.cancerimagingarchive.net/download/attachments/22516629/mass_case_description_test_set.csv?api=v2",
    "calc_train": "https://wiki.cancerimagingarchive.net/download/attachments/22516629/calc_case_description_train_set.csv?api=v2",
    "calc_test": "https://wiki.cancerimagingarchive.net/download/attachments/22516629/calc_case_description_test_set.csv?api=v2",
    "dicom_info": "https://wiki.cancerimagingarchive.net/download/attachments/22516629/dicom_info.csv?api=v2",
}


OUTPUT_FIELDS = [
    "dataset",
    "split",
    "abnormality_type",
    "patient_id",
    "breast_density",
    "left_or_right_breast",
    "image_view",
    "abnormality_id",
    "assessment",
    "pathology",
    "is_malignant",
    "subtlety",
    "image_file_path",
    "cropped_image_file_path",
    "roi_mask_file_path",
    "mass_shape",
    "mass_margins",
    "calc_type",
    "calc_distribution",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def download_file(url: str, destination: Path, force: bool = False) -> None:
    if destination.exists() and not force:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "datathon-cbis"})
            with urllib.request.urlopen(request, timeout=180) as response:
                with temporary.open("wb") as handle:
                    shutil.copyfileobj(response, handle, length=1024 * 1024)
            temporary.rename(destination)
            return
        except (OSError, TimeoutError, urllib.error.URLError) as error:
            last_error = error
            if temporary.exists():
                temporary.unlink()
            if attempt < 3:
                time.sleep(10 * attempt)

    raise RuntimeError(f"Could not download {url}: {last_error}")


def env_url(name: str, default: str) -> str:
    return os.environ.get(f"CBIS_{name.upper()}_URL", default)


def normalize_header(header: str) -> str:
    return header.strip().lower().replace(" ", "_")


def read_case_csv(path: Path, split: str, abnormality_type: str) -> list[dict[str, str]]:
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no header")

        for raw_row in reader:
            row = {normalize_header(key): value for key, value in raw_row.items()}
            pathology = row.get("pathology", "").strip()
            rows.append(
                {
                    "dataset": "CBIS-DDSM",
                    "split": split,
                    "abnormality_type": abnormality_type,
                    "patient_id": row.get("patient_id", ""),
                    "breast_density": row.get("breast_density", ""),
                    "left_or_right_breast": row.get("left_or_right_breast", ""),
                    "image_view": row.get("image_view", ""),
                    "abnormality_id": row.get("abnormality_id", ""),
                    "assessment": row.get("assessment", ""),
                    "pathology": pathology,
                    "is_malignant": str(int("MALIGNANT" in pathology.upper())),
                    "subtlety": row.get("subtlety", ""),
                    "image_file_path": row.get("image_file_path", ""),
                    "cropped_image_file_path": row.get("cropped_image_file_path", ""),
                    "roi_mask_file_path": row.get("roi_mask_file_path", ""),
                    "mass_shape": row.get("mass_shape", ""),
                    "mass_margins": row.get("mass_margins", ""),
                    "calc_type": row.get("calc_type", ""),
                    "calc_distribution": row.get("calc_distribution", ""),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> None:
    args = parse_args()
    labels_dir = args.output.resolve() / "labels"
    raw_dir = labels_dir / "raw"
    labels_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    downloads = {
        name: raw_dir / f"{name}.csv"
        for name in DEFAULT_URLS
    }
    for name, destination in downloads.items():
        url = env_url(name, DEFAULT_URLS[name])
        print(f"Downloading {name}: {url}", flush=True)
        download_file(url, destination, args.force)

    rows: list[dict[str, str]] = []
    rows.extend(read_case_csv(downloads["mass_train"], "train", "mass"))
    rows.extend(read_case_csv(downloads["mass_test"], "test", "mass"))
    rows.extend(read_case_csv(downloads["calc_train"], "train", "calcification"))
    rows.extend(read_case_csv(downloads["calc_test"], "test", "calcification"))

    write_csv(labels_dir / "cbis_ddsm_labels.csv", rows, OUTPUT_FIELDS)

    readme = """# CBIS-DDSM labels

`cbis_ddsm_labels.csv` merges the official CBIS-DDSM case-description CSVs.

Suggested initial datathon task: classify breast lesion pathology from the
mammography images.

- Target column: `is_malignant`
- Original pathology column: `pathology`
- Useful stratification columns: `split`, `abnormality_type`, `assessment`,
  `breast_density`, `left_or_right_breast`, and `image_view`

The raw official CSV files are preserved in `labels/raw/`.
"""
    (labels_dir / "README_labels.md").write_text(readme, encoding="utf-8")
    print(f"Wrote {len(rows):,} CBIS-DDSM label rows to {labels_dir}")


if __name__ == "__main__":
    main()

