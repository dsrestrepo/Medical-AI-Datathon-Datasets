#!/usr/bin/env python3
"""Build the clean MIMIC-CXR datathon dataset."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from dataset_utils import (
    copy_images,
    create_staging_directory,
    publish_staging_directory,
    read_datathon_readme,
    remove_staging_directory,
    validate_unique_image,
)


SPLIT_FILES = (
    ("train_preproc.csv", "train.csv"),
    ("valid_preproc.csv", "valid.csv"),
    ("test_preproc.csv", "test.csv"),
)
REMOVED_COLUMNS = {
    "",
    "Unnamed: 0",
    "path",
    "path_preproc",
    "text_path",
    "filepath",
    "disease",
    "disease_label",
    "class_label",
}

README = """# MIMIC-CXR - subconjunto para el Datathon

## Descripción

Subconjunto de MIMIC-CXR con radiografías de tórax preprocesadas a
224x224 píxeles. Incluye metadatos de los estudios, información demográfica,
etiquetas derivadas de los reportes radiológicos y el reporte completo en la
columna `report`.

Dataset original: https://physionet.org/content/mimic-cxr/

## Estructura

```text
MIMIC-CXR/
├── images/       # Todas las imágenes JPG
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

La columna `image` contiene únicamente el nombre del archivo. Para abrir una
imagen, combine la ruta de este dataset con la carpeta `images/`.

## Etiquetas

Las etiquetas disponibles son:

- Atelectasis
- Cardiomegaly
- Consolidation
- Edema
- Enlarged Cardiomediastinum
- Fracture
- Lung Lesion
- Lung Opacity
- No Finding
- Pleural Effusion
- Pleural Other
- Pneumonia
- Pneumothorax
- Support Devices

Para estas etiquetas, `1` indica presencia, `0` ausencia, `-1` incertidumbre y
un valor vacío indica que no existe una etiqueta disponible.

También se incluyen metadatos del estudio y variables demográficas como raza,
sexo y edad. Las columnas internas `disease`, `disease_label` y `class_label`
fueron retiradas porque duplicaban o mezclaban información derivable de las
etiquetas anteriores.

## Reportes

La columna `report` contiene el reporte radiológico completo asociado con la
imagen. Esta versión incluye únicamente registros de los CSV `*_preproc.csv`
que tienen un reporte disponible.

## Ejemplo de lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/MIMIC-CXR")
metadata = pd.read_csv(root / "train.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])
```
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--clean-existing",
        action="store_true",
        help=(
            "Update an existing clean MIMIC-CXR folder in place by removing "
            "retired columns from train/valid/test CSVs and refreshing README.md."
        ),
    )
    return parser.parse_args()


def clean_existing_output(output: Path) -> None:
    if not output.is_dir():
        raise FileNotFoundError(f"Existing clean MIMIC-CXR folder not found: {output}")

    for split_csv in ("train.csv", "valid.csv", "test.csv"):
        path = output / split_csv
        if not path.is_file():
            raise FileNotFoundError(f"Missing split CSV: {path}")

        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with path.open("r", encoding="utf-8", newline="") as source_handle:
            reader = csv.DictReader(source_handle)
            if not reader.fieldnames:
                raise ValueError(f"{path} has no header")
            output_fields = [field for field in reader.fieldnames if field not in REMOVED_COLUMNS]
            if "image" not in output_fields:
                raise ValueError(f"{path} must contain an image column")

            with temporary_path.open("w", encoding="utf-8", newline="") as output_handle:
                writer = csv.DictWriter(output_handle, fieldnames=output_fields)
                writer.writeheader()
                for row in reader:
                    writer.writerow({field: row.get(field, "") for field in output_fields})

        temporary_path.replace(path)
        print(f"Updated {path}: removed retired columns if present", flush=True)

    (output / "README.md").write_text(
        read_datathon_readme("MIMIC-CXR.md"),
        encoding="utf-8",
    )
    print(f"Refreshed {output / 'README.md'}", flush=True)


def main() -> None:
    args = parse_args()
    output = args.output.resolve()

    if args.clean_existing:
        clean_existing_output(output)
        return

    source = args.source.resolve()
    image_source = source / "preproc_224x224"

    if not source.is_dir():
        raise FileNotFoundError(f"MIMIC source directory does not exist: {source}")
    if not image_source.is_dir():
        raise FileNotFoundError(f"MIMIC image directory does not exist: {image_source}")
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")

    staging = create_staging_directory(args.output)
    image_tasks: list[tuple[Path, str]] = []
    seen_images: dict[str, Path] = {}

    try:
        for input_name, output_name in SPLIT_FILES:
            input_csv = source / input_name
            if not input_csv.is_file():
                raise FileNotFoundError(f"Missing report-bearing split CSV: {input_csv}")

            output_csv = staging / output_name
            row_count = 0

            with input_csv.open("r", encoding="utf-8", newline="") as source_handle:
                reader = csv.DictReader(source_handle)
                required_columns = {"path_preproc", "report"}
                if not reader.fieldnames or not required_columns <= set(reader.fieldnames):
                    raise ValueError(
                        f"{input_csv} must contain path_preproc and report columns"
                    )

                output_fields = [
                    "image",
                    *[field for field in reader.fieldnames if field not in REMOVED_COLUMNS],
                ]

                with output_csv.open("w", encoding="utf-8", newline="") as output_handle:
                    writer = csv.DictWriter(output_handle, fieldnames=output_fields)
                    writer.writeheader()

                    for row in reader:
                        relative_path = row.get("path_preproc", "")
                        if not relative_path:
                            raise ValueError(
                                f"Missing path_preproc in {input_csv}, row {row_count + 2}"
                            )
                        if not row.get("report", "").strip():
                            raise ValueError(
                                f"Missing report in {input_csv}, row {row_count + 2}"
                            )

                        image_name = Path(relative_path).name
                        source_image = source / relative_path
                        validate_unique_image(seen_images, image_name, source_image)
                        image_tasks.append((source_image, image_name))

                        clean_row = {"image": image_name}
                        clean_row.update(
                            {
                                field: row.get(field, "")
                                for field in output_fields
                                if field != "image"
                            }
                        )
                        writer.writerow(clean_row)
                        row_count += 1

            print(
                f"Prepared {output_name} from {input_name}: {row_count:,} rows",
                flush=True,
            )

        copy_images(image_tasks, staging / "images", args.workers)
        (staging / "README.md").write_text(
            read_datathon_readme("MIMIC-CXR.md"),
            encoding="utf-8",
        )
        publish_staging_directory(staging, args.output)
    except Exception:
        remove_staging_directory(staging)
        raise

    print(f"Published clean MIMIC-CXR dataset at {args.output.resolve()}")


if __name__ == "__main__":
    main()
