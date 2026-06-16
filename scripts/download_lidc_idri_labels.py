#!/usr/bin/env python3
"""Download/parse official LIDC-IDRI XML annotations into CSV labels."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree


LIDC_XML_URL_CANDIDATES = [
    "https://wiki.cancerimagingarchive.net/download/attachments/1966254/LIDC-XML-only.zip?api=v2",
    "https://wiki.cancerimagingarchive.net/download/attachments/1966254/LIDC-IDRI-XML.zip?api=v2",
    "https://wiki.cancerimagingarchive.net/download/attachments/3539039/LIDC-XML-only.zip?api=v2",
    "https://wiki.cancerimagingarchive.net/download/attachments/3539039/LIDC-IDRI-XML.zip?api=v2",
]


ANNOTATION_FIELDS = [
    "dataset",
    "patient_id",
    "xml_file",
    "series_instance_uid",
    "study_instance_uid",
    "reader_id",
    "nodule_id",
    "nodule_type",
    "subtlety",
    "internal_structure",
    "calcification",
    "sphericity",
    "margin",
    "lobulation",
    "spiculation",
    "texture",
    "malignancy",
    "roi_count",
    "sop_instance_uids",
]

NODULE_LABEL_FIELDS = [
    "dataset",
    "annotation_id",
    "patient_id",
    "xml_file",
    "series_instance_uid",
    "study_instance_uid",
    "reader_id",
    "nodule_id",
    "malignancy",
    "malignancy_class",
    "subtlety",
    "internal_structure",
    "calcification",
    "sphericity",
    "margin",
    "lobulation",
    "spiculation",
    "texture",
    "roi_count",
    "sop_instance_uids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--xml-zip", type=Path, default=None)
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
            request = urllib.request.Request(url, headers={"User-Agent": "datathon-lidc"})
            with urllib.request.urlopen(request, timeout=600) as response:
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


def get_xml_archive(raw_dir: Path, provided: Path | None, force: bool) -> Path:
    if provided is not None:
        if not provided.is_file():
            raise FileNotFoundError(f"Provided XML zip does not exist: {provided}")
        return provided

    destination = raw_dir / "lidc_xml_annotations.zip"
    if destination.exists() and not force:
        return destination

    urls = []
    if os.environ.get("LIDC_XML_URL"):
        urls.append(os.environ["LIDC_XML_URL"])
    urls.extend(LIDC_XML_URL_CANDIDATES)

    errors = []
    for url in urls:
        try:
            print(f"Downloading LIDC XML annotations: {url}", flush=True)
            download_file(url, destination, force)
            return destination
        except Exception as error:
            errors.append(f"{url}: {error}")

    raise RuntimeError(
        "Could not download the official LIDC XML annotations. Set LIDC_XML_URL "
        "to the XML zip URL from the official TCIA LIDC-IDRI page, or pass "
        "--xml-zip. Tried:\n" + "\n".join(errors)
    )


def local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def first_text(element: ElementTree.Element, names: set[str]) -> str:
    for child in element.iter():
        if local_name(child) in names and child.text:
            return child.text.strip()
    return ""


def direct_child_text(element: ElementTree.Element, name: str) -> str:
    for child in list(element):
        if local_name(child) == name and child.text:
            return child.text.strip()
    return ""


def find_children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element.iter() if local_name(child) == name]


def parse_xml_file(path: Path, relative_name: str) -> list[dict[str, str]]:
    tree = ElementTree.parse(path)
    root = tree.getroot()
    patient_id = first_text(root, {"patientID", "PatientID"})
    if not patient_id:
        for part in Path(relative_name).parts:
            if part.startswith("LIDC-IDRI-"):
                patient_id = part
                break
    series_uid = first_text(root, {"seriesInstanceUid", "SeriesInstanceUid"})
    study_uid = first_text(root, {"studyInstanceUID", "StudyInstanceUID"})
    rows = []

    for session_index, session in enumerate(find_children(root, "readingSession"), start=1):
        reader_id = direct_child_text(session, "servicingRadiologistID") or str(session_index)

        for nodule in list(session):
            tag = local_name(nodule)
            if tag not in {"unblindedReadNodule", "nonNodule"}:
                continue

            nodule_id = direct_child_text(nodule, "noduleID") or direct_child_text(
                nodule, "nonNoduleID"
            )
            characteristics = next(
                (child for child in list(nodule) if local_name(child) == "characteristics"),
                None,
            )

            sop_uids = []
            for roi in [child for child in list(nodule) if local_name(child) == "roi"]:
                sop_uid = direct_child_text(roi, "imageSOP_UID")
                if sop_uid:
                    sop_uids.append(sop_uid)

            row = {
                "dataset": "LIDC-IDRI",
                "patient_id": patient_id,
                "xml_file": relative_name,
                "series_instance_uid": series_uid,
                "study_instance_uid": study_uid,
                "reader_id": reader_id,
                "nodule_id": nodule_id,
                "nodule_type": "nodule" if tag == "unblindedReadNodule" else "non_nodule",
                "roi_count": str(len(sop_uids)),
                "sop_instance_uids": "|".join(sorted(set(sop_uids))),
            }

            for name, output_name in [
                ("subtlety", "subtlety"),
                ("internalStructure", "internal_structure"),
                ("calcification", "calcification"),
                ("sphericity", "sphericity"),
                ("margin", "margin"),
                ("lobulation", "lobulation"),
                ("spiculation", "spiculation"),
                ("texture", "texture"),
                ("malignancy", "malignancy"),
            ]:
                row[output_name] = (
                    direct_child_text(characteristics, name) if characteristics is not None else ""
                )
            rows.append(row)

    return rows


def malignancy_class(value: float) -> str:
    if value <= 2:
        return "benign_or_low_suspicion"
    if value >= 4:
        return "malignant_or_high_suspicion"
    return "indeterminate"


def build_nodule_labels(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    labels = []
    for row in rows:
        if row["nodule_type"] != "nodule" or not row.get("malignancy"):
            continue
        malignancy = float(row["malignancy"])
        annotation_id = "|".join(
            [
                row.get("xml_file", ""),
                row.get("reader_id", ""),
                row.get("nodule_id", ""),
            ]
        )
        labels.append(
            {
                "dataset": "LIDC-IDRI",
                "annotation_id": annotation_id,
                "patient_id": row.get("patient_id", ""),
                "xml_file": row.get("xml_file", ""),
                "series_instance_uid": row.get("series_instance_uid", ""),
                "study_instance_uid": row.get("study_instance_uid", ""),
                "reader_id": row.get("reader_id", ""),
                "nodule_id": row.get("nodule_id", ""),
                "malignancy": row.get("malignancy", ""),
                "malignancy_class": malignancy_class(malignancy),
                "subtlety": row.get("subtlety", ""),
                "internal_structure": row.get("internal_structure", ""),
                "calcification": row.get("calcification", ""),
                "sphericity": row.get("sphericity", ""),
                "margin": row.get("margin", ""),
                "lobulation": row.get("lobulation", ""),
                "spiculation": row.get("spiculation", ""),
                "texture": row.get("texture", ""),
                "roi_count": row.get("roi_count", ""),
                "sop_instance_uids": row.get("sop_instance_uids", ""),
            }
        )
    return labels


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

    archive = get_xml_archive(raw_dir, args.xml_zip, args.force)
    annotation_rows: list[dict[str, str]] = []

    with tempfile.TemporaryDirectory(dir=str(raw_dir)) as temporary_dir:
        extract_dir = Path(temporary_dir) / "xml"
        extract_dir.mkdir()
        with zipfile.ZipFile(archive) as zip_handle:
            zip_handle.extractall(extract_dir)

        xml_files = sorted(extract_dir.rglob("*.xml"))
        if not xml_files:
            raise ValueError(f"No XML files found in {archive}")

        for xml_file in xml_files:
            relative_name = xml_file.relative_to(extract_dir).as_posix()
            annotation_rows.extend(parse_xml_file(xml_file, relative_name))

    nodule_label_rows = build_nodule_labels(annotation_rows)
    write_csv(labels_dir / "lidc_idri_reader_annotations.csv", annotation_rows, ANNOTATION_FIELDS)
    write_csv(labels_dir / "lidc_idri_nodule_labels.csv", nodule_label_rows, NODULE_LABEL_FIELDS)

    readme = """# LIDC-IDRI labels

`lidc_idri_reader_annotations.csv` contains one row per radiologist annotation
for nodules and non-nodules parsed from the official LIDC-IDRI XML files.

`lidc_idri_nodule_labels.csv` keeps one supervised example per radiologist
nodule annotation. Suggested initial datathon task: predict the annotated nodule
malignancy class from CT image data.

- Regression target: `malignancy`
- Classification target: `malignancy_class`
- Join keys: `patient_id`, `series_instance_uid`, and the SOP Instance UIDs in
  `lidc_idri_reader_annotations.csv`

The raw official XML archive is preserved in `labels/raw/`.
"""
    (labels_dir / "README_labels.md").write_text(readme, encoding="utf-8")
    print(
        f"Wrote {len(annotation_rows):,} LIDC reader annotations and "
        f"{len(nodule_label_rows):,} nodule labels to {labels_dir}"
    )


if __name__ == "__main__":
    main()
