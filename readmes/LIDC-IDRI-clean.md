# LIDC-IDRI Clean Dataset / Dataset limpio LIDC-IDRI

## English

### Dataset Description

This folder contains a simplified LIDC-IDRI dataset prepared for the Medical AI Datathon.
Each CT series was converted from many DICOM slices into one compressed `.npz`
volume. Labels are provided at three levels because the original LIDC-IDRI
annotations are not simple CT-level labels.

Original dataset: https://www.cancerimagingarchive.net/collection/lidc-idri/

### Structure

```text
LIDC-IDRI-clean-{size}/
├── volumes/
├── reader_level.csv
├── nodule_level.csv
├── ct_level.csv
├── preprocessing_summary.json
└── README.md
```

### Files

- `volumes/`: compressed `.npz` files, one per CT series.
- `ct_level.csv`: one row per CT series, with derived aggregate labels.
- `reader_level.csv`: one row per radiologist annotation.
- `nodule_level.csv`: one row per approximate nodule group.
- `preprocessing_summary.json`: counts and preprocessing summary.
- `README.md`: this file.

### Volume Format

Each `.npz` file contains:

- `volume`: 3D array with shape `(height, width, slices)`.
- `series_instance_uid`: DICOM series identifier.
- `patient_id`: patient identifier.

The volumes were converted to Hounsfield Units, clipped to a lung window of
`{window_min}` to `{window_max}` HU, normalized to `float16` values between 0
and 1, and resized slice by slice to `{size}x{size}` pixels. The number of
slices is kept variable.

### Main Variables in `ct_level.csv`

- `volume_path`: relative path to the `.npz` volume.
- `split`: patient-level train/test split.
- `patient_id`, `study_instance_uid`, `series_instance_uid`: DICOM identifiers.
- `num_slices`, `height`, `width`: processed volume shape.
- `array_axis_order`: array convention, always `height,width,slices`.
- `original_num_slices`, `original_height`, `original_width`: original CT size.
- `spacing_z_mm`, `spacing_y_mm`, `spacing_x_mm`: processed spacing metadata.
- `original_spacing_z_mm`, `original_spacing_y_mm`, `original_spacing_x_mm`:
  original DICOM spacing metadata.
- `window_min_hu`, `window_max_hu`: HU clipping window.
- `n_reader_annotations`: number of labelled nodule annotations in the CT.
- `n_nodule_groups`: number of approximate nodule groups in the CT.
- `n_annotated_slices`: number of slices referenced by annotations.
- `malignancy_scores`: all available malignancy scores joined by `|`.
- `max_malignancy`, `mean_malignancy`, `median_malignancy`: CT-level aggregate
  malignancy scores.
- `has_malignant_or_high_suspicion`: binary target, 1 if any annotation has
  malignancy >= 4.
- `ct_malignancy_class`: CT-level class derived from `max_malignancy`.

### Main Variables in `reader_level.csv`

- `reader_id`: radiologist/reader identifier.
- `nodule_id`: nodule identifier from the parsed annotations.
- `nodule_type`: nodule or non-nodule.
- `malignancy`: reader malignancy score, when available.
- `subtlety`, `internal_structure`, `calcification`, `sphericity`, `margin`,
  `lobulation`, `spiculation`, `texture`: reader-assigned nodule
  characteristics.
- `roi_count`: number of ROI slices for that annotation.
- `sop_instance_uids`: DICOM slice identifiers referenced by the annotation.

### Main Variables in `nodule_level.csv`

- `nodule_group_id`: approximate nodule group identifier.
- `n_reader_annotations`: number of annotations grouped for that nodule.
- `reader_ids`, `annotation_ids`: source annotations.
- `malignancy_scores`, `max_malignancy`, `mean_malignancy`,
  `median_malignancy`: aggregated malignancy labels.
- `nodule_malignancy_class`: nodule-level class derived from max malignancy.
- `roi_count_total`, `sop_instance_uids`: ROI coverage metadata.

### Possible Tasks

- CT-level suspicious nodule / malignancy-risk classification using
  `has_malignant_or_high_suspicion`.
- CT-level multiclass classification using `ct_malignancy_class`.
- Reader-level analysis using `reader_level.csv`.
- Approximate nodule-level analysis using `nodule_level.csv`.

Important: `ct_level.csv` contains derived CT-level labels. The original
LIDC-IDRI labels are annotation/nodule-level radiologist annotations.

### Loading Example

```python
from pathlib import Path
import numpy as np
import pandas as pd

root = Path("PATH-TO-DATASET/LIDC-IDRI-clean-{size}")
ct_labels = pd.read_csv(root / "ct_level.csv")
row = ct_labels.iloc[0]
data = np.load(root / row["volume_path"])
volume = data["volume"]  # shape: (height, width, slices)
```

## Español

### Descripción del Dataset

Esta carpeta contiene una versión simplificada de LIDC-IDRI preparada para el Medical AI Datathon. Cada serie CT fue convertida desde múltiples slices DICOM a un único
volumen comprimido `.npz`. Las etiquetas se entregan en tres niveles porque las
anotaciones originales de LIDC-IDRI no son etiquetas simples a nivel de CT.

Dataset original: https://www.cancerimagingarchive.net/collection/lidc-idri/

### Estructura

```text
LIDC-IDRI-clean-{size}/
├── volumes/
├── reader_level.csv
├── nodule_level.csv
├── ct_level.csv
├── preprocessing_summary.json
└── README.md
```

### Archivos

- `volumes/`: archivos `.npz` comprimidos, uno por serie CT.
- `ct_level.csv`: una fila por serie CT, con etiquetas agregadas derivadas.
- `reader_level.csv`: una fila por anotación de radiólogo/lector.
- `nodule_level.csv`: una fila por grupo aproximado de nódulo.
- `preprocessing_summary.json`: conteos y resumen de preprocesamiento.
- `README.md`: este archivo.

### Formato del Volumen

Cada archivo `.npz` contiene:

- `volume`: arreglo 3D con forma `(height, width, slices)`.
- `series_instance_uid`: identificador DICOM de la serie.
- `patient_id`: identificador del paciente.

Los volúmenes fueron convertidos a unidades Hounsfield, recortados a una
ventana pulmonar de `{window_min}` a `{window_max}` HU, normalizados a valores
`float16` entre 0 y 1, y redimensionados slice por slice a `{size}x{size}`
píxeles. El número de slices se mantiene variable.

### Variables Principales en `ct_level.csv`

- `volume_path`: ruta relativa al volumen `.npz`.
- `split`: partición train/test asignada a nivel de paciente.
- `patient_id`, `study_instance_uid`, `series_instance_uid`: identificadores
  DICOM.
- `num_slices`, `height`, `width`: forma del volumen procesado.
- `array_axis_order`: convención del arreglo, siempre `height,width,slices`.
- `original_num_slices`, `original_height`, `original_width`: tamaño original
  del CT.
- `spacing_z_mm`, `spacing_y_mm`, `spacing_x_mm`: spacing procesado.
- `original_spacing_z_mm`, `original_spacing_y_mm`, `original_spacing_x_mm`:
  spacing original del DICOM.
- `window_min_hu`, `window_max_hu`: ventana HU usada.
- `n_reader_annotations`: número de anotaciones de nódulos etiquetadas en la CT.
- `n_nodule_groups`: número de grupos aproximados de nódulos en la CT.
- `n_annotated_slices`: número de slices referenciados por anotaciones.
- `malignancy_scores`: puntuaciones de malignidad separadas por `|`.
- `max_malignancy`, `mean_malignancy`, `median_malignancy`: agregados de
  malignidad a nivel CT.
- `has_malignant_or_high_suspicion`: target binario, 1 si alguna anotación
  tiene malignidad >= 4.
- `ct_malignancy_class`: clase CT-level derivada de `max_malignancy`.

### Variables Principales en `reader_level.csv`

- `reader_id`: identificador del radiólogo/lector.
- `nodule_id`: identificador del nódulo en las anotaciones procesadas.
- `nodule_type`: nódulo o no-nódulo.
- `malignancy`: puntuación de malignidad del lector, si existe.
- `subtlety`, `internal_structure`, `calcification`, `sphericity`, `margin`,
  `lobulation`, `spiculation`, `texture`: características asignadas por el
  lector.
- `roi_count`: número de slices ROI para esa anotación.
- `sop_instance_uids`: identificadores DICOM de slices referenciados.

### Variables Principales en `nodule_level.csv`

- `nodule_group_id`: identificador aproximado del grupo de nódulo.
- `n_reader_annotations`: número de anotaciones agrupadas para ese nódulo.
- `reader_ids`, `annotation_ids`: anotaciones fuente.
- `malignancy_scores`, `max_malignancy`, `mean_malignancy`,
  `median_malignancy`: etiquetas de malignidad agregadas.
- `nodule_malignancy_class`: clase a nivel de nódulo derivada de la malignidad
  máxima.
- `roi_count_total`, `sop_instance_uids`: metadatos de cobertura ROI.

### Tareas Posibles

- Clasificación CT-level de riesgo/sospecha de nódulo maligno usando
  `has_malignant_or_high_suspicion`.
- Clasificación multiclase CT-level usando `ct_malignancy_class`.
- Análisis a nivel de lector usando `reader_level.csv`.
- Análisis aproximado a nivel de nódulo usando `nodule_level.csv`.

Importante: `ct_level.csv` contiene etiquetas CT-level derivadas. Las etiquetas
originales de LIDC-IDRI son anotaciones radiológicas a nivel de anotación/nódulo.

### Ejemplo de Lectura

```python
from pathlib import Path
import numpy as np
import pandas as pd

root = Path("PATH-TO-DATASET/LIDC-IDRI-clean-{size}")
ct_labels = pd.read_csv(root / "ct_level.csv")
row = ct_labels.iloc[0]
data = np.load(root / row["volume_path"])
volume = data["volume"]  # shape: (height, width, slices)
```
