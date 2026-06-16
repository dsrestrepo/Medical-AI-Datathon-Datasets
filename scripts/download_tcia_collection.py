#!/usr/bin/env python3
"""Download a TCIA collection into a simple images + labels layout."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


DEFAULT_API_BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
DEFAULT_EXCLUDED_MODALITIES = {"SEG", "RTSTRUCT", "SR", "PR"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--modality",
        action="append",
        default=[],
        help="Modality to include. Can be passed multiple times.",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-series", type=int, default=None)
    parser.add_argument("--keep-zip", action="store_true")
    parser.add_argument(
        "--api-base",
        default=os.environ.get("TCIA_API_BASE", DEFAULT_API_BASE),
        help="NBIA REST API base URL.",
    )
    return parser.parse_args()


def api_url(api_base: str, endpoint: str, **params: str) -> str:
    return f"{api_base.rstrip('/')}/{endpoint}?{urllib.parse.urlencode(params)}"


def fetch_json(url: str, retries: int = 3) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "datathon-tcia"})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read().decode("utf-8")
            data = json.loads(payload)
            if not isinstance(data, list):
                raise ValueError(f"Expected a JSON list from {url}")
            return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == retries:
                break
            time.sleep(10 * attempt)
    raise RuntimeError(f"Failed to fetch JSON from {url}: {last_error}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = sorted({key for row in rows for key in row})
    else:
        fieldnames = []

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def filter_series(
    series: list[dict[str, Any]], included_modalities: set[str]
) -> list[dict[str, Any]]:
    selected = []
    for row in series:
        modality = str(row.get("Modality", "")).upper()
        if included_modalities and modality not in included_modalities:
            continue
        if not included_modalities and modality in DEFAULT_EXCLUDED_MODALITIES:
            continue
        selected.append(row)
    return selected


def download_file(url: str, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "datathon-tcia"})
            with urllib.request.urlopen(request, timeout=600) as response:
                with temporary.open("wb") as handle:
                    shutil.copyfileobj(response, handle, length=1024 * 1024)
            temporary.rename(destination)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if temporary.exists():
                temporary.unlink()
            if attempt == retries:
                break
            time.sleep(30 * attempt)
    raise RuntimeError(f"Failed to download {url}: {last_error}")


def safe_series_name(series_uid: str) -> str:
    return series_uid.replace("/", "_")


def download_and_extract_series(
    api_base: str,
    series_uid: str,
    image_root: Path,
    archive_root: Path,
    keep_zip: bool,
) -> None:
    series_dir = image_root / safe_series_name(series_uid)
    done_marker = series_dir / ".download_complete"
    if done_marker.exists():
        return

    url = api_url(api_base, "getImage", SeriesInstanceUID=series_uid)
    with tempfile.TemporaryDirectory(dir=str(archive_root)) as temporary_dir:
        zip_path = Path(temporary_dir) / f"{safe_series_name(series_uid)}.zip"
        download_file(url, zip_path)

        extraction_dir = image_root / f".{safe_series_name(series_uid)}.extracting"
        if extraction_dir.exists():
            shutil.rmtree(extraction_dir)
        extraction_dir.mkdir(parents=True)

        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extraction_dir)
            done_marker.parent.mkdir(parents=True, exist_ok=True)
            if series_dir.exists():
                shutil.rmtree(series_dir)
            extraction_dir.rename(series_dir)
            done_marker.write_text("ok\n", encoding="utf-8")
            if keep_zip:
                archive_root.mkdir(parents=True, exist_ok=True)
                shutil.copy2(zip_path, archive_root / zip_path.name)
        except Exception:
            if extraction_dir.exists():
                shutil.rmtree(extraction_dir)
            raise


def build_image_manifest(
    output: Path,
    image_root: Path,
    selected_series: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    series_by_uid = {
        str(row["SeriesInstanceUID"]): row
        for row in selected_series
        if "SeriesInstanceUID" in row
    }
    manifest = []

    for series_uid, series_row in sorted(series_by_uid.items()):
        series_dir = image_root / safe_series_name(series_uid)
        if not series_dir.is_dir():
            continue

        for path in sorted(series_dir.rglob("*")):
            if not path.is_file() or path.name == ".download_complete":
                continue
            relative_path = path.relative_to(output).as_posix()
            manifest.append(
                {
                    "image_path": relative_path,
                    "file_name": path.name,
                    "SeriesInstanceUID": series_uid,
                    "StudyInstanceUID": series_row.get("StudyInstanceUID", ""),
                    "PatientID": series_row.get("PatientID", ""),
                    "Modality": series_row.get("Modality", ""),
                    "BodyPartExamined": series_row.get("BodyPartExamined", ""),
                    "SeriesDescription": series_row.get("SeriesDescription", ""),
                    "StudyDate": series_row.get("StudyDate", ""),
                    "SeriesNumber": series_row.get("SeriesNumber", ""),
                }
            )

    return manifest


def write_readme(output: Path, collection: str, modalities: set[str]) -> None:
    modality_text = ", ".join(sorted(modalities)) if modalities else "all non-SEG modalities"
    label_note = {
        "LIDC-IDRI": (
            "LIDC-IDRI task labels are the radiologist nodule annotations "
            "(including nodule characteristics such as malignancy). They are "
            "not contained in the CT DICOM pixels downloaded by this generic "
            "NBIA job, so a separate LIDC annotation parsing step is still "
            "needed before this becomes a supervised challenge dataset."
        ),
        "CBIS-DDSM": (
            "CBIS-DDSM task labels such as pathology, assessment, breast "
            "density, abnormality type, and image/case split come from the "
            "collection's case-description CSV files. Those CSV labels are "
            "not produced by this generic NBIA image-only job yet, so a "
            "separate CBIS label download/merge step is still needed before "
            "this becomes a supervised challenge dataset."
        ),
    }.get(
        collection,
        "This generic download provides image files and TCIA/NBIA metadata. "
        "Collection-specific task labels may require an additional step.",
    )

    readme = f"""# {collection}

Downloaded from The Cancer Imaging Archive using the NBIA REST API.

## Layout

```text
{collection}/
├── images/                 # DICOM files grouped by SeriesInstanceUID
├── labels/
│   ├── all_series.csv       # All series metadata returned by TCIA
│   ├── downloaded_series.csv
│   └── image_manifest.csv   # One row per downloaded DICOM file
└── README.md
```

This initial datathon version downloads only imaging data for modalities:
{modality_text}. Segmentation-specific assets are intentionally not downloaded
in this first pass.

`labels/image_manifest.csv` is the main file participants should start from. It
contains one row per downloaded DICOM file, with a relative `image_path` and the
series/study/patient identifiers needed to join back to
`labels/downloaded_series.csv`.

## Label status

{label_note}
"""
    (output / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")

    output = args.output.resolve()
    labels_dir = output / "labels"
    images_dir = output / "images"
    archives_dir = output / "archives"
    output.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    archives_dir.mkdir(exist_ok=True)

    included_modalities = {modality.upper() for modality in args.modality}

    series_url = api_url(args.api_base, "getSeries", Collection=args.collection)
    print(f"Fetching series metadata: {series_url}", flush=True)
    all_series = fetch_json(series_url)
    write_csv(labels_dir / "all_series.csv", all_series)
    (labels_dir / "all_series.json").write_text(
        json.dumps(all_series, indent=2, sort_keys=True), encoding="utf-8"
    )

    selected_series = filter_series(all_series, included_modalities)
    if args.max_series is not None:
        selected_series = selected_series[: args.max_series]
    if not selected_series:
        raise ValueError("No series matched the requested filters")

    write_csv(labels_dir / "downloaded_series.csv", selected_series)
    write_readme(output, args.collection, included_modalities)

    remaining_series = [
        row
        for row in selected_series
        if not (images_dir / safe_series_name(str(row["SeriesInstanceUID"])) / ".download_complete").exists()
    ]

    print(
        f"Downloading {len(remaining_series):,} remaining series "
        f"out of {len(selected_series):,} selected "
        f"({len(all_series):,} total TCIA series) into {images_dir}",
        flush=True,
    )

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                download_and_extract_series,
                args.api_base,
                str(row["SeriesInstanceUID"]),
                images_dir,
                archives_dir,
                args.keep_zip,
            )
            for row in remaining_series
        ]
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 25 == 0 or completed == len(remaining_series):
                print(
                    f"Downloaded {completed:,}/{len(remaining_series):,} remaining series",
                    flush=True,
                )

    if not args.keep_zip and archives_dir.exists():
        try:
            archives_dir.rmdir()
        except OSError:
            pass

    image_manifest = build_image_manifest(output, images_dir, selected_series)
    write_rows(
        labels_dir / "image_manifest.csv",
        image_manifest,
        [
            "image_path",
            "file_name",
            "SeriesInstanceUID",
            "StudyInstanceUID",
            "PatientID",
            "Modality",
            "BodyPartExamined",
            "SeriesDescription",
            "StudyDate",
            "SeriesNumber",
        ],
    )
    print(f"Wrote image manifest with {len(image_manifest):,} DICOM files", flush=True)

    print(f"Finished {args.collection}: {output}")


if __name__ == "__main__":
    main()
