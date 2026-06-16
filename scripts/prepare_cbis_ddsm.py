#!/usr/bin/env python3
"""Create a clean 224x224 full-image CBIS-DDSM datathon dataset."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

from dataset_utils import read_datathon_readme

try:
    import numpy as np
    from PIL import Image
except ImportError as error:
    raise RuntimeError(
        "prepare_cbis_ddsm.py requires numpy and Pillow. Use the same conda "
        "environment as the CT/image workflows, or install them before running "
        "the Slurm job."
    ) from error


CASE_FILES = [
    ("mass_train.csv", "train", "mass"),
    ("mass_test.csv", "test", "mass"),
    ("calc_train.csv", "train", "calcification"),
    ("calc_test.csv", "test", "calcification"),
]

LABEL_FIELDS = [
    "image",
    "split",
    "patient_id",
    "left_or_right_breast",
    "image_view",
    "abnormality_id",
    "abnormality_type",
    "assessment",
    "breast_density",
    "pathology",
    "is_malignant",
    "subtlety",
    "mass_shape",
    "mass_margins",
    "calc_type",
    "calc_distribution",
    "source_case_csv",
    "source_image_file_path",
    "source_series_instance_uid",
]

README = """# CBIS-DDSM - versión limpia para el Datathon

## Descripción

Esta carpeta contiene una versión simplificada de CBIS-DDSM para tareas de
clasificación de lesiones mamarias. Se incluyen únicamente las mamografías
completas redimensionadas a 224x224 píxeles y una tabla compacta de etiquetas.

Dataset original: https://www.cancerimagingarchive.net/collection/cbis-ddsm/

## Estructura

```text
CBIS-DDSM-clean/
├── images/      # imágenes PNG 224x224
├── labels.csv
└── README.md
```

La columna `image` contiene únicamente el nombre del archivo dentro de
`images/`.

## Tareas posibles

La tarea principal recomendada para el datathon es clasificación binaria
benigno vs maligno.

- Target principal: `is_malignant`
- Etiqueta original: `pathology`
- Metadatos útiles: `abnormality_type`, `assessment`, `breast_density`,
  `image_view`, `left_or_right_breast`

Otras tareas posibles con el mismo `labels.csv`:

- Clasificación multiclase de patología usando `pathology`.
- Clasificación de tipo de hallazgo usando `abnormality_type` (masa vs
  calcificación).
- Predicción de categoría BI-RADS/assessment usando `assessment`.
- Análisis por subgrupos usando `breast_density`, `image_view` o lateralidad.

Las imágenes originales son DICOM de alta resolución. Para facilitar el uso en
el datathon, cada mamografía completa se convierte a escala de grises, se aplica
una normalización robusta usando percentiles 1 y 99, y se redimensiona a
224x224 píxeles.

La carpeta final no incluye crops ni máscaras ROI para mantener el dataset
simple.

## Ejemplo de lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/CBIS-DDSM-clean")
labels = pd.read_csv(root / "labels.csv")
image = Image.open(root / "images" / labels.loc[0, "image"])
```
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=224)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_case_rows(raw_dir: Path) -> list[dict[str, str]]:
    rows = []
    for filename, split, abnormality_type in CASE_FILES:
        path = raw_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing CBIS case CSV: {path}")
        for row in read_csv(path):
            normalized = {normalize_header(key): value for key, value in row.items()}
            normalized["split"] = split
            normalized["abnormality_type"] = normalized.get("abnormality_type", abnormality_type)
            normalized["source_case_csv"] = filename
            rows.append(normalized)
    return rows


def series_uid_from_label_path(value: str) -> str:
    parts = [part for part in str(value).replace("\\", "/").split("/") if part]
    if len(parts) < 2:
        return ""
    return parts[-2]


def build_manifest_index(source: Path) -> dict[str, Path]:
    manifest_path = source / "labels" / "image_manifest.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing image manifest: {manifest_path}")

    index: dict[str, Path] = {}
    for row in read_csv(manifest_path):
        series_uid = row.get("SeriesInstanceUID", "")
        image_path = row.get("image_path", "")
        file_name = row.get("file_name", "")
        description = row.get("SeriesDescription", "").lower()
        if not series_uid or not image_path:
            continue
        if not file_name.lower().endswith(".dcm"):
            continue
        if "full mammogram" not in description:
            continue
        index.setdefault(series_uid, source / image_path)
    return index


def dicom_to_uint8(path: Path) -> np.ndarray:
    try:
        import pydicom
    except ImportError as error:
        raise RuntimeError(
            "prepare_cbis_ddsm.py requires pydicom to read CBIS DICOM images."
        ) from error

    dataset = pydicom.dcmread(str(path))
    array = dataset.pixel_array.astype(np.float32)

    if getattr(dataset, "PhotometricInterpretation", "") == "MONOCHROME1":
        array = array.max() - array

    low, high = np.percentile(array, [1, 99])
    if high <= low:
        low, high = float(array.min()), float(array.max())
    if high <= low:
        return np.zeros(array.shape, dtype=np.uint8)

    array = np.clip((array - low) / (high - low), 0, 1)
    return (array * 255).astype(np.uint8)


def resize_and_save(source: Path, destination: Path, size: int) -> None:
    array = dicom_to_uint8(source)
    image = Image.fromarray(array, mode="L")
    image = image.resize((size, size), Image.Resampling.BILINEAR)
    image.save(destination)


def output_name(row: dict[str, str], index: int) -> str:
    parts = [
        row.get("split", ""),
        row.get("abnormality_type", ""),
        row.get("patient_id", ""),
        row.get("left_or_right_breast", ""),
        row.get("image_view", ""),
        row.get("abnormality_id", ""),
        str(index),
    ]
    clean = ["".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in part) for part in parts]
    return "_".join(part for part in clean if part) + ".png"


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()

    if output.exists():
        if not args.overwrite:
            raise FileExistsError(f"Output exists: {output}. Pass --overwrite to rebuild.")
        shutil.rmtree(output)

    raw_dir = source / "labels" / "raw"
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Missing raw label directory: {raw_dir}")

    rows = load_case_rows(raw_dir)
    manifest_index = build_manifest_index(source)

    output.mkdir(parents=True)
    image_dir = output / "images"
    image_dir.mkdir()

    label_rows: list[dict[str, str]] = []
    mapping_rows: list[dict[str, str]] = []
    missing = 0

    for index, row in enumerate(rows, start=1):
        source_image_file_path = row.get("image_file_path", "")
        series_uid = series_uid_from_label_path(source_image_file_path)
        dicom_path = manifest_index.get(series_uid)
        if dicom_path is None or not dicom_path.is_file():
            missing += 1
            mapping_rows.append(
                {
                    "source_case_csv": row.get("source_case_csv", ""),
                    "source_image_file_path": source_image_file_path,
                    "source_series_instance_uid": series_uid,
                    "status": "missing_full_mammogram_dicom",
                    "output_image": "",
                }
            )
            continue

        image_name = output_name(row, index)
        resize_and_save(dicom_path, image_dir / image_name, args.size)

        pathology = row.get("pathology", "")
        label_row = {
            "image": image_name,
            "split": row.get("split", ""),
            "patient_id": row.get("patient_id", ""),
            "left_or_right_breast": row.get("left_or_right_breast", ""),
            "image_view": row.get("image_view", ""),
            "abnormality_id": row.get("abnormality_id", ""),
            "abnormality_type": row.get("abnormality_type", ""),
            "assessment": row.get("assessment", ""),
            "breast_density": row.get("breast_density", ""),
            "pathology": pathology,
            "is_malignant": str(int("MALIGNANT" in pathology.upper())),
            "subtlety": row.get("subtlety", ""),
            "mass_shape": row.get("mass_shape", ""),
            "mass_margins": row.get("mass_margins", ""),
            "calc_type": row.get("calc_type", ""),
            "calc_distribution": row.get("calc_distribution", ""),
            "source_case_csv": row.get("source_case_csv", ""),
            "source_image_file_path": source_image_file_path,
            "source_series_instance_uid": series_uid,
        }
        label_rows.append(label_row)
        mapping_rows.append(
            {
                "source_case_csv": row.get("source_case_csv", ""),
                "source_image_file_path": source_image_file_path,
                "source_series_instance_uid": series_uid,
                "status": "ok",
                "output_image": image_name,
            }
        )

        if len(label_rows) % 250 == 0:
            print(f"Processed {len(label_rows):,} images", flush=True)

    write_csv(output / "labels.csv", label_rows, LABEL_FIELDS)
    if missing:
        write_csv(
            output / "mapping_report.csv",
            mapping_rows,
            [
                "source_case_csv",
                "source_image_file_path",
                "source_series_instance_uid",
                "status",
                "output_image",
            ],
        )
    (output / "README.md").write_text(
        read_datathon_readme("CBIS-DDSM-clean.md"),
        encoding="utf-8",
    )

    print(f"Wrote {len(label_rows):,} resized full mammograms to {output}")
    print(f"Missing mappings: {missing:,}/{len(rows):,}")
    if not label_rows:
        raise RuntimeError("No CBIS images were processed; check manifest/label mapping.")


if __name__ == "__main__":
    main()
