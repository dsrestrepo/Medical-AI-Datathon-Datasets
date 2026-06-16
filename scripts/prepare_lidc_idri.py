#!/usr/bin/env python3
"""Create clean full-volume LIDC-IDRI datathon datasets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from dataset_utils import read_datathon_readme

try:
    import numpy as np
    from PIL import Image
except ImportError as error:
    raise RuntimeError(
        "prepare_lidc_idri.py requires numpy and Pillow. Use the same conda "
        "environment as the CT/image workflows, or install them before running "
        "the Slurm job."
    ) from error


WINDOW_MIN = -1000.0
WINDOW_MAX = 400.0

README_TEMPLATE = """# LIDC-IDRI - versión limpia para el Datathon

## Descripción

Esta carpeta contiene una versión simplificada de LIDC-IDRI para trabajar con
volúmenes CT 3D completos. Cada serie CT fue convertida desde múltiples slices
DICOM a un único archivo `.npz`.

Dataset original: https://www.cancerimagingarchive.net/collection/lidc-idri/

## Estructura

```text
LIDC-IDRI-clean-{size}/
├── volumes/                  # Volúmenes CT en formato .npz
├── reader_level.csv          # Una fila por anotación de lector/radiólogo
├── nodule_level.csv          # Una fila por grupo de nódulo aproximado
├── ct_level.csv              # Una fila por CT/serie, con etiquetas agregadas
└── README.md
```

## Formato de los volúmenes

Cada archivo `.npz` contiene:

- `volume`: arreglo 3D con forma `(height, width, slices)`.
- `series_instance_uid`: identificador DICOM de la serie CT.
- `patient_id`: identificador del paciente.

Los volúmenes fueron:

1. Convertidos a unidades Hounsfield.
2. Recortados a una ventana pulmonar de `{window_min}` a `{window_max}` HU.
3. Normalizados a valores `float16` entre 0 y 1.
4. Redimensionados slice por slice a `{size}x{size}` píxeles.

El número de slices se mantiene variable para preservar la
cobertura original de cada CT. En los CSV se incluyen tanto el spacing original
como el spacing procesado después del reescalado.

Ejemplo:

```python
from pathlib import Path
import numpy as np
import pandas as pd

# Reemplazar con tu ruta al dataset
root = Path("PATH-TO-DATASET/LIDC-IDRI-clean-{size}")
ct_labels = pd.read_csv(root / "ct_level.csv")

row = ct_labels.iloc[0]
data = np.load(root / row["volume_path"])
volume = data["volume"]  # shape: (height, width, slices)
```

## Archivos de etiquetas

### `reader_level.csv`

Una fila por anotación de lector/radiólogo. Este es el nivel más cercano a las
anotaciones originales de LIDC-IDRI. Incluye nódulos y no-nódulos cuando están
presentes en las anotaciones.

### `nodule_level.csv`

Una fila por grupo de nódulo aproximado dentro de una serie CT. Las etiquetas
de malignidad se agregan a partir de las anotaciones disponibles para ese grupo.

Nota: esta agrupación usa los identificadores disponibles en los XML procesados.
No debe interpretarse como una reconstrucción perfecta del consenso de
los cuatro lectores.

### `ct_level.csv`

Una fila por CT/serie. Las etiquetas son agregadas desde las anotaciones de
nódulos. Por ejemplo:

- `max_malignancy`: máxima puntuación de malignidad observada en la CT.
- `has_malignant_or_high_suspicion`: 1 si alguna anotación tiene malignidad >= 4.
- `ct_malignancy_class`: clase derivada desde `max_malignancy`.

Este archivo define una tarea CT-level derivada, no una etiqueta original de
LIDC-IDRI.

## Tareas posibles

- Clasificación CT-level: predecir si una CT contiene al menos una anotación de
  alta sospecha o malignidad (`has_malignant_or_high_suspicion`).
- Clasificación ordinal o multiclase usando `ct_malignancy_class`.
- Tareas más avanzadas usando `reader_level.csv` o `nodule_level.csv`.

## Splits

La columna `split` se asigna a nivel de paciente para evitar fuga de información
entre train y test.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def parse_float(value: Any) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_multi_float(value: str) -> list[float]:
    values = []
    for part in str(value or "").replace(",", "\\").split("\\"):
        part = part.strip()
        if not part:
            continue
        parsed = parse_float(part)
        if parsed is not None:
            values.append(parsed)
    return values


def malignancy_class_from_max(value: float | None) -> str:
    if value is None:
        return "no_label"
    if value <= 2:
        return "benign_or_low_suspicion"
    if value >= 4:
        return "malignant_or_high_suspicion"
    return "indeterminate"


def split_for_patient(patient_id: str, seed: int, test_fraction: float) -> str:
    key = f"{seed}:{patient_id}".encode("utf-8")
    value = int(hashlib.sha1(key).hexdigest()[:12], 16) / float(16**12)
    return "test" if value < test_fraction else "train"


def safe_series_name(series_uid: str, index: int) -> str:
    digest = hashlib.sha1(series_uid.encode("utf-8")).hexdigest()[:12]
    return f"lidc_ct_{index:04d}_{digest}.npz"


def prepare_output(output: Path, overwrite: bool) -> None:
    if output.exists() or output.is_symlink():
        if not overwrite:
            raise FileExistsError(
                f"Output already exists: {output}. Move it or pass --overwrite."
            )
        if output.is_symlink() or output.is_file():
            output.unlink()
        else:
            shutil.rmtree(output)
    (output / "volumes").mkdir(parents=True)


def read_dicom_pixels(path: Path) -> tuple[np.ndarray, dict[str, str]]:
    try:
        import pydicom  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "prepare_lidc_idri.py requires pydicom to read DICOM files."
        ) from error

    ds = pydicom.dcmread(str(path), force=True)
    array = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    array = array * slope + intercept
    header = {
        "SOPInstanceUID": str(getattr(ds, "SOPInstanceUID", "")),
        "InstanceNumber": str(getattr(ds, "InstanceNumber", "")),
        "ImagePositionPatient": "\\".join(
            map(str, getattr(ds, "ImagePositionPatient", []))
        ),
        "Rows": str(getattr(ds, "Rows", "")),
        "Columns": str(getattr(ds, "Columns", "")),
        "PixelSpacing": "\\".join(map(str, getattr(ds, "PixelSpacing", []))),
        "SliceThickness": str(getattr(ds, "SliceThickness", "")),
    }
    return array, header


def resize_slice_hu(array: np.ndarray, size: int) -> np.ndarray:
    clipped = np.clip(array, WINDOW_MIN, WINDOW_MAX)
    normalized = (clipped - WINDOW_MIN) / (WINDOW_MAX - WINDOW_MIN)
    image = Image.fromarray(normalized.astype(np.float32), mode="F")
    resampling = getattr(Image, "Resampling", Image).BILINEAR
    resized = image.resize((size, size), resample=resampling)
    return np.asarray(resized, dtype=np.float32)


def sort_key_from_header(header: dict[str, str]) -> tuple[int, float]:
    z_values = parse_multi_float(header.get("ImagePositionPatient", ""))
    if len(z_values) >= 3:
        return (0, z_values[2])
    if z_values:
        return (0, z_values[0])
    instance = parse_float(header.get("InstanceNumber", ""))
    if instance is not None:
        return (1, instance)
    return (2, 0.0)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def unique_join(values: list[str]) -> str:
    return "|".join(sorted({value for value in values if value}))


def number_join(values: list[float]) -> str:
    return "|".join(str(int(value)) if value.is_integer() else str(value) for value in values)


def summarize_malignancies(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "malignancy_scores": "",
            "max_malignancy": "",
            "mean_malignancy": "",
            "median_malignancy": "",
            "has_malignant_or_high_suspicion": 0,
            "has_indeterminate": 0,
            "has_benign_or_low_suspicion": 0,
            "ct_malignancy_class": "no_label",
        }

    max_value = max(values)
    return {
        "malignancy_scores": number_join(values),
        "max_malignancy": max_value,
        "mean_malignancy": sum(values) / len(values),
        "median_malignancy": median(values),
        "has_malignant_or_high_suspicion": int(any(value >= 4 for value in values)),
        "has_indeterminate": int(any(value == 3 for value in values)),
        "has_benign_or_low_suspicion": int(any(value <= 2 for value in values)),
        "ct_malignancy_class": malignancy_class_from_max(max_value),
    }


def main() -> None:
    args = parse_args()
    if args.size < 1:
        raise ValueError("--size must be positive")
    if not 0 < args.test_fraction < 1:
        raise ValueError("--test-fraction must be between 0 and 1")

    source = args.source.resolve()
    output = args.output.resolve()
    labels_dir = source / "labels"

    manifest_rows = read_csv(labels_dir / "image_manifest.csv")
    reader_rows = read_csv(labels_dir / "lidc_idri_reader_annotations.csv")
    nodule_label_rows = read_csv(labels_dir / "lidc_idri_nodule_labels.csv")

    prepare_output(output, args.overwrite)

    manifest_by_series: dict[str, list[dict[str, str]]] = defaultdict(list)
    patient_by_series: dict[str, str] = {}
    study_by_series: dict[str, str] = {}
    for row in manifest_rows:
        series_uid = row.get("SeriesInstanceUID", "")
        if not series_uid:
            continue
        manifest_by_series[series_uid].append(row)
        if row.get("PatientID"):
            patient_by_series[series_uid] = row["PatientID"]
        if row.get("StudyInstanceUID"):
            study_by_series[series_uid] = row["StudyInstanceUID"]

    labelled_series = {
        row.get("series_instance_uid", "")
        for row in reader_rows + nodule_label_rows
        if row.get("series_instance_uid", "")
    }
    series_uids = sorted(set(manifest_by_series) & labelled_series)
    if not series_uids:
        raise RuntimeError("No labelled CT series found to preprocess.")

    split_by_patient = {
        patient_id: split_for_patient(patient_id, args.seed, args.test_fraction)
        for patient_id in sorted({patient for patient in patient_by_series.values() if patient})
    }
    split_by_series = {}
    for series_uid in series_uids:
        patient_id = patient_by_series.get(series_uid, series_uid)
        split_by_series[series_uid] = split_by_patient.get(
            patient_id,
            split_for_patient(series_uid, args.seed, args.test_fraction),
        )

    volume_rows: dict[str, dict[str, Any]] = {}

    for index, series_uid in enumerate(series_uids, start=1):
        rows = manifest_by_series[series_uid]
        seen_sops: set[str] = set()
        slice_records: list[tuple[tuple[int, float], np.ndarray, dict[str, str], str]] = []
        spacing_y_values: list[float] = []
        spacing_x_values: list[float] = []
        slice_thickness_values: list[float] = []
        original_heights: list[float] = []
        original_widths: list[float] = []

        for row in rows:
            image_path = row.get("image_path", "")
            if not image_path:
                continue
            path = source / image_path
            if not path.is_file():
                continue

            array, dicom_header = read_dicom_pixels(path)
            sop_uid = dicom_header.get("SOPInstanceUID", "")
            if sop_uid and sop_uid in seen_sops:
                continue
            if sop_uid:
                seen_sops.add(sop_uid)
            slice_records.append(
                (
                    sort_key_from_header(dicom_header),
                    resize_slice_hu(array, args.size),
                    dicom_header,
                    image_path,
                )
            )

            spacing = parse_multi_float(dicom_header["PixelSpacing"])
            if len(spacing) >= 2:
                spacing_y_values.append(spacing[0])
                spacing_x_values.append(spacing[1])
            thickness = parse_float(dicom_header["SliceThickness"])
            if thickness is not None:
                slice_thickness_values.append(thickness)
            original_height = parse_float(dicom_header["Rows"])
            original_width = parse_float(dicom_header["Columns"])
            if original_height is not None:
                original_heights.append(original_height)
            if original_width is not None:
                original_widths.append(original_width)

        if not slice_records:
            print(f"Skipping {series_uid}: no readable slices", flush=True)
            continue

        slice_records.sort(key=lambda item: item[0])
        slices = [record[1] for record in slice_records]
        volume = np.stack(slices, axis=-1).astype(np.float16)
        volume_name = safe_series_name(series_uid, index)
        np.savez_compressed(
            output / "volumes" / volume_name,
            volume=volume,
            series_instance_uid=np.asarray(series_uid),
            patient_id=np.asarray(patient_by_series.get(series_uid, "")),
        )

        original_height = median(original_heights)
        original_width = median(original_widths)
        original_spacing_z = median(slice_thickness_values)
        original_spacing_y = median(spacing_y_values)
        original_spacing_x = median(spacing_x_values)
        processed_spacing_y = (
            original_spacing_y * float(original_height) / float(args.size)
            if original_spacing_y is not None and original_height is not None
            else None
        )
        processed_spacing_x = (
            original_spacing_x * float(original_width) / float(args.size)
            if original_spacing_x is not None and original_width is not None
            else None
        )
        volume_rows[series_uid] = {
            "volume_path": f"volumes/{volume_name}",
            "patient_id": patient_by_series.get(series_uid, ""),
            "study_instance_uid": study_by_series.get(series_uid, ""),
            "series_instance_uid": series_uid,
            "split": split_by_series[series_uid],
            "num_slices": volume.shape[-1],
            "height": volume.shape[0],
            "width": volume.shape[1],
            "array_axis_order": "height,width,slices",
            "original_num_slices": len(rows),
            "original_height": int(original_height) if original_height is not None else "",
            "original_width": int(original_width) if original_width is not None else "",
            "spacing_z_mm": original_spacing_z or "",
            "spacing_y_mm": processed_spacing_y or "",
            "spacing_x_mm": processed_spacing_x or "",
            "original_spacing_z_mm": original_spacing_z or "",
            "original_spacing_y_mm": original_spacing_y or "",
            "original_spacing_x_mm": original_spacing_x or "",
            "window_min_hu": WINDOW_MIN,
            "window_max_hu": WINDOW_MAX,
        }

        if index == 1 or index % 25 == 0 or index == len(series_uids):
            print(
                f"Processed {index:,}/{len(series_uids):,} CT series "
                f"({volume.shape[0]}x{volume.shape[1]}x{volume.shape[2]})",
                flush=True,
            )

    processed_series = set(volume_rows)

    def enrich_row(row: dict[str, str]) -> dict[str, Any]:
        series_uid = row.get("series_instance_uid", "")
        volume = volume_rows.get(series_uid, {})
        output_row: dict[str, Any] = dict(row)
        output_row.update(
            {
                "volume_path": volume.get("volume_path", ""),
                "patient_id": row.get("patient_id") or volume.get("patient_id", ""),
                "study_instance_uid": row.get("study_instance_uid") or volume.get("study_instance_uid", ""),
                "split": volume.get("split", ""),
                "height": volume.get("height", ""),
                "width": volume.get("width", ""),
                "num_slices": volume.get("num_slices", ""),
                "array_axis_order": volume.get("array_axis_order", ""),
                "spacing_z_mm": volume.get("spacing_z_mm", ""),
                "spacing_y_mm": volume.get("spacing_y_mm", ""),
                "spacing_x_mm": volume.get("spacing_x_mm", ""),
                "original_spacing_z_mm": volume.get("original_spacing_z_mm", ""),
                "original_spacing_y_mm": volume.get("original_spacing_y_mm", ""),
                "original_spacing_x_mm": volume.get("original_spacing_x_mm", ""),
            }
        )
        return output_row

    reader_output_rows = [
        enrich_row(row)
        for row in reader_rows
        if row.get("series_instance_uid", "") in processed_series
    ]
    reader_fields = [
        "volume_path",
        "split",
        "patient_id",
        "study_instance_uid",
        "series_instance_uid",
        "reader_id",
        "nodule_id",
        "nodule_type",
        "malignancy",
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
        "height",
        "width",
        "num_slices",
        "array_axis_order",
        "spacing_z_mm",
        "spacing_y_mm",
        "spacing_x_mm",
        "original_spacing_z_mm",
        "original_spacing_y_mm",
        "original_spacing_x_mm",
        "xml_file",
    ]
    write_csv(output / "reader_level.csv", reader_output_rows, reader_fields)

    nodule_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in nodule_label_rows:
        series_uid = row.get("series_instance_uid", "")
        if series_uid not in processed_series:
            continue
        nodule_groups[(series_uid, row.get("nodule_id", ""))].append(enrich_row(row))

    nodule_output_rows = []
    for (series_uid, nodule_id), rows in sorted(nodule_groups.items()):
        first = rows[0]
        malignancies = [
            value
            for value in (parse_float(row.get("malignancy", "")) for row in rows)
            if value is not None
        ]
        summary = summarize_malignancies(malignancies)
        nodule_output_rows.append(
            {
                "volume_path": first.get("volume_path", ""),
                "split": first.get("split", ""),
                "patient_id": first.get("patient_id", ""),
                "study_instance_uid": first.get("study_instance_uid", ""),
                "series_instance_uid": series_uid,
                "nodule_id": nodule_id,
                "nodule_group_id": f"{series_uid}|{nodule_id}",
                "n_reader_annotations": len(rows),
                "reader_ids": unique_join([row.get("reader_id", "") for row in rows]),
                "annotation_ids": unique_join([row.get("annotation_id", "") for row in rows]),
                "malignancy_scores": summary["malignancy_scores"],
                "max_malignancy": summary["max_malignancy"],
                "mean_malignancy": summary["mean_malignancy"],
                "median_malignancy": summary["median_malignancy"],
                "nodule_malignancy_class": summary["ct_malignancy_class"],
                "subtlety_scores": number_join(
                    [
                        value
                        for value in (parse_float(row.get("subtlety", "")) for row in rows)
                        if value is not None
                    ]
                ),
                "texture_scores": number_join(
                    [
                        value
                        for value in (parse_float(row.get("texture", "")) for row in rows)
                        if value is not None
                    ]
                ),
                "roi_count_total": sum(int(parse_float(row.get("roi_count", "")) or 0) for row in rows),
                "sop_instance_uids": unique_join(
                    uid
                    for row in rows
                    for uid in str(row.get("sop_instance_uids", "")).split("|")
                ),
                "height": first.get("height", ""),
                "width": first.get("width", ""),
                "num_slices": first.get("num_slices", ""),
                "array_axis_order": first.get("array_axis_order", ""),
                "spacing_z_mm": first.get("spacing_z_mm", ""),
                "spacing_y_mm": first.get("spacing_y_mm", ""),
                "spacing_x_mm": first.get("spacing_x_mm", ""),
                "original_spacing_z_mm": first.get("original_spacing_z_mm", ""),
                "original_spacing_y_mm": first.get("original_spacing_y_mm", ""),
                "original_spacing_x_mm": first.get("original_spacing_x_mm", ""),
            }
        )

    nodule_fields = [
        "volume_path",
        "split",
        "patient_id",
        "study_instance_uid",
        "series_instance_uid",
        "nodule_id",
        "nodule_group_id",
        "n_reader_annotations",
        "reader_ids",
        "annotation_ids",
        "malignancy_scores",
        "max_malignancy",
        "mean_malignancy",
        "median_malignancy",
        "nodule_malignancy_class",
        "subtlety_scores",
        "texture_scores",
        "roi_count_total",
        "sop_instance_uids",
        "height",
        "width",
        "num_slices",
        "array_axis_order",
        "spacing_z_mm",
        "spacing_y_mm",
        "spacing_x_mm",
        "original_spacing_z_mm",
        "original_spacing_y_mm",
        "original_spacing_x_mm",
    ]
    write_csv(output / "nodule_level.csv", nodule_output_rows, nodule_fields)

    malignancies_by_series: dict[str, list[float]] = defaultdict(list)
    nodule_ids_by_series: dict[str, list[str]] = defaultdict(list)
    annotation_ids_by_series: dict[str, list[str]] = defaultdict(list)
    annotated_sops_by_series: dict[str, set[str]] = defaultdict(set)
    for row in nodule_label_rows:
        series_uid = row.get("series_instance_uid", "")
        if series_uid not in processed_series:
            continue
        value = parse_float(row.get("malignancy", ""))
        if value is not None:
            malignancies_by_series[series_uid].append(value)
        nodule_ids_by_series[series_uid].append(row.get("nodule_id", ""))
        annotation_ids_by_series[series_uid].append(row.get("annotation_id", ""))
        for uid in str(row.get("sop_instance_uids", "")).split("|"):
            if uid:
                annotated_sops_by_series[series_uid].add(uid)

    ct_output_rows = []
    for series_uid, volume in sorted(volume_rows.items()):
        values = malignancies_by_series.get(series_uid, [])
        summary = summarize_malignancies(values)
        ct_output_rows.append(
            {
                **volume,
                "n_reader_annotations": len(values),
                "n_nodule_groups": len(set(nodule_ids_by_series.get(series_uid, []))),
                "n_annotated_slices": len(annotated_sops_by_series.get(series_uid, set())),
                "nodule_ids": unique_join(nodule_ids_by_series.get(series_uid, [])),
                "annotation_ids": unique_join(annotation_ids_by_series.get(series_uid, [])),
                **summary,
            }
        )

    ct_fields = [
        "volume_path",
        "split",
        "patient_id",
        "study_instance_uid",
        "series_instance_uid",
        "num_slices",
        "height",
        "width",
        "array_axis_order",
        "original_num_slices",
        "original_height",
        "original_width",
        "spacing_z_mm",
        "spacing_y_mm",
        "spacing_x_mm",
        "original_spacing_z_mm",
        "original_spacing_y_mm",
        "original_spacing_x_mm",
        "window_min_hu",
        "window_max_hu",
        "n_reader_annotations",
        "n_nodule_groups",
        "n_annotated_slices",
        "nodule_ids",
        "annotation_ids",
        "malignancy_scores",
        "max_malignancy",
        "mean_malignancy",
        "median_malignancy",
        "has_malignant_or_high_suspicion",
        "has_indeterminate",
        "has_benign_or_low_suspicion",
        "ct_malignancy_class",
    ]
    write_csv(output / "ct_level.csv", ct_output_rows, ct_fields)

    readme = read_datathon_readme("LIDC-IDRI-clean.md").format(
        size=args.size,
        window_min=int(WINDOW_MIN),
        window_max=int(WINDOW_MAX),
    )
    (output / "README.md").write_text(readme, encoding="utf-8")

    summary = {
        "source": str(source),
        "output": str(output),
        "size": args.size,
        "series_processed": len(volume_rows),
        "reader_level_rows": len(reader_output_rows),
        "nodule_level_rows": len(nodule_output_rows),
        "ct_level_rows": len(ct_output_rows),
        "split_counts": Counter(row["split"] for row in ct_output_rows),
        "ct_label_counts": Counter(row["ct_malignancy_class"] for row in ct_output_rows),
    }
    (output / "preprocessing_summary.json").write_text(
        json.dumps(summary, indent=2, default=dict),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, default=dict), flush=True)


if __name__ == "__main__":
    main()
