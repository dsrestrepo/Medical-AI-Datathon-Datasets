#!/usr/bin/env python3
"""Build the clean mBRSET datathon dataset."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dataset_utils import (
    create_staging_directory,
    publish_staging_directory,
    read_datathon_readme,
    remove_staging_directory,
    validate_unique_image,
)

try:
    from PIL import Image
except ImportError as error:
    raise RuntimeError(
        "prepare_mbrset.py requires Pillow to resize images."
    ) from error


README = """# mBRSET - versión para el Datathon

## Descripción

mBRSET (Mobile Brazilian Retinal Dataset) contiene fotografías de fondo de ojo
adquiridas con cámaras portátiles en escenarios clínicos reales en Brasil. El
dataset incluye variables clínicas y demográficas útiles para estudiar
retinopatía diabética, glaucoma, robustez, sesgos, entre otras.

Dataset original: https://physionet.org/content/mbrset/
Paper: https://www.nature.com/articles/s41597-025-04627-3

Esta versión limpia incluye las imágenes en resolución de 448x448. `metadata.csv` contiene exactamente
una fila por imagen incluida.

## Estructura

```text
mBRSET/
├── images/       # Todas las imágenes JPG preprocesadas a 448x448 píxeles
├── metadata.csv
└── README.md
```

La columna `image` contiene únicamente el nombre del archivo. Para abrir una
imagen, combine la ruta de este dataset con `images/` y el valor de `image`.

La columna `split` asigna todos los registros de un mismo paciente al mismo
conjunto (`train`, `val` o `test`) para evitar fuga de información.

## Etiquetas y metadatos

- `final_icdr`: grado de retinopatía diabética según ICDR, de 0 a 4.
- `final_edema`: presencia de edema.
- `increased_cdr`: relación copa-disco aumentada (Glaucoma).
- `final_quality` y `final_artifacts`: calidad y artefactos de la imagen.
- Variables clínicas: diabetes, tratamientos, hipertensión, obesidad,
  enfermedad vascular, nefropatía, neuropatía y pie diabético.
- Variables demográficas: edad, sexo, seguro y nivel educativo.

## Ejemplo de lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/mBRSET")
metadata = pd.read_csv(root / "metadata.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])
```
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image-folder", default="images")
    parser.add_argument("--size", type=int, default=448)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_patient_splits(path: Path) -> dict[str, str]:
    patient_splits: dict[str, str] = {}

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"patient", "split"} <= set(reader.fieldnames):
            raise ValueError(f"{path} must contain patient and split columns")

        for row in reader:
            patient = row["patient"]
            split = row["split"]
            previous = patient_splits.get(patient)
            if previous is not None and previous != split:
                raise ValueError(
                    f"Patient {patient} appears in multiple splits: {previous}, {split}"
                )
            patient_splits[patient] = split

    return patient_splits


def resize_images(
    image_sources: list[tuple[Path, str]],
    destination: Path,
    size: int,
    workers: int,
) -> None:
    destination.mkdir()

    def resize_one(task: tuple[Path, str]) -> None:
        source, image_name = task
        if not source.is_file():
            raise FileNotFoundError(f"Missing source image: {source}")
        with Image.open(source) as image:
            image = image.convert("RGB")
            image = image.resize((size, size), Image.Resampling.BILINEAR)
            image.save(destination / image_name, quality=95)

    completed = 0
    batch_size = max(workers * 100, 1_000)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(image_sources), batch_size):
            batch = image_sources[start : start + batch_size]
            futures = [executor.submit(resize_one, task) for task in batch]
            for future in as_completed(futures):
                future.result()
                completed += 1
                if completed % 10_000 == 0 or completed == len(image_sources):
                    print(
                        f"Resized {completed:,}/{len(image_sources):,} images",
                        flush=True,
                    )


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    labels_csv = source / "labels.csv"
    splits_csv = source / "labels_splits.csv"
    image_source = source / args.image_folder

    for required_path in (labels_csv, splits_csv, image_source):
        if not required_path.exists():
            raise FileNotFoundError(f"Required mBRSET path does not exist: {required_path}")
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.size < 1:
        raise ValueError("--size must be at least 1")
    if args.output.exists() and args.overwrite:
        remove_staging_directory(args.output)

    patient_splits = read_patient_splits(splits_csv)
    available_images = {
        entry.name
        for entry in os.scandir(image_source)
        if entry.is_file(follow_symlinks=False)
    }
    if not available_images:
        raise ValueError(f"No images found in {image_source}")

    staging = create_staging_directory(args.output)
    image_tasks: list[tuple[Path, str]] = []
    seen_images: dict[str, Path] = {}
    seen_patients: set[str] = set()

    try:
        with labels_csv.open("r", encoding="utf-8", newline="") as source_handle:
            reader = csv.DictReader(source_handle)
            if not reader.fieldnames or not {"patient", "file"} <= set(reader.fieldnames):
                raise ValueError(f"{labels_csv} must contain patient and file columns")

            output_fields = [
                "image",
                "split",
                *[field for field in reader.fieldnames if field != "file"],
            ]

            with (staging / "metadata.csv").open(
                "w", encoding="utf-8", newline=""
            ) as output_handle:
                writer = csv.DictWriter(output_handle, fieldnames=output_fields)
                writer.writeheader()

                row_count = 0
                skipped_missing_images = 0
                for row in reader:
                    patient = row["patient"]
                    if patient not in patient_splits:
                        raise ValueError(f"Patient {patient} has no split assignment")

                    image_name = Path(row["file"]).name
                    if image_name not in available_images:
                        skipped_missing_images += 1
                        continue

                    source_image = image_source / image_name
                    validate_unique_image(seen_images, image_name, source_image)
                    image_tasks.append((source_image, image_name))
                    seen_patients.add(patient)

                    clean_row = {"image": image_name, "split": patient_splits[patient]}
                    clean_row.update(
                        {
                            field: row.get(field, "")
                            for field in output_fields
                            if field not in {"image", "split"}
                        }
                    )
                    writer.writerow(clean_row)
                    row_count += 1

        if not image_tasks:
            raise ValueError("No metadata rows matched the available images")

        print(
            f"Prepared metadata.csv: {row_count:,} rows for "
            f"{len(seen_patients):,} patients",
            flush=True,
        )
        print(
            f"Skipped {skipped_missing_images:,} metadata rows whose images "
            f"are not present in {args.image_folder}",
            flush=True,
        )
        resize_images(image_tasks, staging / "images", args.size, args.workers)
        (staging / "README.md").write_text(
            read_datathon_readme("mBRSET.md"),
            encoding="utf-8",
        )
        publish_staging_directory(staging, args.output)
    except Exception:
        remove_staging_directory(staging)
        raise

    print(f"Published clean mBRSET dataset at {args.output.resolve()}")


if __name__ == "__main__":
    main()
