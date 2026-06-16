# MIMIC-CXR Clean Dataset / Dataset limpio MIMIC-CXR

## English

### Dataset Description

This folder contains a clean MIMIC-CXR subset prepared for the Medical AI Datathon. Images
are preprocessed chest X-rays stored as JPG files. The CSV files include study
metadata, demographic variables, CheXpert-style labels, and the full radiology
report in the `report` column.

Original dataset: https://physionet.org/content/mimic-cxr/

### Structure

```text
MIMIC-CXR/
├── images/
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

The `image` column contains only the image filename. To load an image, combine
the dataset path, `images/`, and the value in `image`.

### Files

- `images/`: chest X-ray JPG files.
- `train.csv`, `valid.csv`, `test.csv`: split files with image names, metadata,
  labels, and reports.
- `README.md`: this file.

### Main Variables

- `image`: image filename inside `images/`.
- `dicom_id`, `subject_id`, `study_id`: identifiers for the image, patient, and
  study.
- `split`: split name.
- `ViewPosition`: radiographic view, for example AP or PA.
- `Rows`, `Columns`: image dimensions.
- `StudyDate`, `StudyTime`: study timing metadata.
- `race`, `sex`, `age`: demographic variables.
- `race_label`, `sex_label`: encoded demographic variables.
- `report`: full radiology report text.

Label columns:

- `Atelectasis`
- `Cardiomegaly`
- `Consolidation`
- `Edema`
- `Enlarged Cardiomediastinum`
- `Fracture`
- `Lung Lesion`
- `Lung Opacity`
- `No Finding`
- `Pleural Effusion`
- `Pleural Other`
- `Pneumonia`
- `Pneumothorax`
- `Support Devices`

For these labels, `1` means present, `0` means absent, `-1` means uncertain,
and an empty value means no label is available.

### Possible Tasks

- Multi-label chest X-ray classification.
- Report-aware or multimodal modeling using the `report` column.
- Subgroup or fairness analysis using metadata such as age, sex, and race.

### Loading Example

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/MIMIC-CXR")
metadata = pd.read_csv(root / "train.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])
```

## Español

### Descripción del Dataset

Esta carpeta contiene un subconjunto limpio de MIMIC-CXR preparado para el Medical AI Datathon. Las imágenes son radiografías de tórax preprocesadas en formato JPG.
Los CSV incluyen metadatos del estudio, variables demográficas, etiquetas tipo
CheXpert y el reporte radiológico completo en la columna `report`.

Dataset original: https://physionet.org/content/mimic-cxr/

### Estructura

```text
MIMIC-CXR/
├── images/
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

La columna `image` contiene solo el nombre del archivo. Para cargar una imagen,
combina la ruta del dataset, `images/` y el valor de `image`.

### Archivos

- `images/`: radiografías de tórax en formato JPG.
- `train.csv`, `valid.csv`, `test.csv`: archivos por split con nombres de
  imagen, metadatos, etiquetas y reportes.
- `README.md`: este archivo.

### Variables Principales

- `image`: nombre del archivo dentro de `images/`.
- `dicom_id`, `subject_id`, `study_id`: identificadores de imagen, paciente y
  estudio.
- `split`: partición del dataset.
- `ViewPosition`: vista radiográfica, por ejemplo AP o PA.
- `Rows`, `Columns`: dimensiones de la imagen.
- `StudyDate`, `StudyTime`: metadatos temporales del estudio.
- `race`, `sex`, `age`: variables demográficas.
- `race_label`, `sex_label`: variables demográficas codificadas.
- `report`: texto completo del reporte radiológico.

Columnas de etiquetas:

- `Atelectasis`
- `Cardiomegaly`
- `Consolidation`
- `Edema`
- `Enlarged Cardiomediastinum`
- `Fracture`
- `Lung Lesion`
- `Lung Opacity`
- `No Finding`
- `Pleural Effusion`
- `Pleural Other`
- `Pneumonia`
- `Pneumothorax`
- `Support Devices`

Para estas etiquetas, `1` indica presencia, `0` ausencia, `-1` incertidumbre y
un valor vacío indica que no hay etiqueta disponible.

### Tareas Posibles

- Clasificación multi-etiqueta de radiografías de tórax.
- Modelado multimodal o con reportes usando la columna `report`.
- Análisis por subgrupos o equidad usando metadatos como edad, sexo y raza.

### Ejemplo de Lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/MIMIC-CXR")
metadata = pd.read_csv(root / "train.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])
```
