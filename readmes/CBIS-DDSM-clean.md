# CBIS-DDSM Clean Dataset / Dataset limpio CBIS-DDSM

## English

### Dataset Description

This folder contains a simplified CBIS-DDSM dataset prepared for the Medical AI Datathon.
It includes resized full mammograms and one compact `labels.csv` file. 

Original dataset: https://www.cancerimagingarchive.net/collection/cbis-ddsm/

### Structure

```text
CBIS-DDSM-clean/
├── images/
├── labels.csv
└── README.md
```

The `image` column contains only the PNG filename inside `images/`.

### Files

- `images/`: resized full mammogram PNG images.
- `labels.csv`: labels and task-relevant metadata.
- `README.md`: this file.

### Main Variables

- `image`: image filename inside `images/`.
- `split`: train/test split from the original CBIS case files.
- `patient_id`: patient identifier.
- `left_or_right_breast`: breast laterality.
- `image_view`: mammography view, for example CC or MLO.
- `abnormality_id`: abnormality identifier within a case.
- `abnormality_type`: mass or calcification.
- `assessment`: BI-RADS-like assessment score.
- `breast_density`: breast density category.
- `pathology`: original pathology label.
- `is_malignant`: binary label derived from `pathology`.
- `subtlety`: subtlety score from the original case description.
- `mass_shape`, `mass_margins`: mass-specific descriptors.
- `calc_type`, `calc_distribution`: calcification-specific descriptors.
- `source_case_csv`, `source_image_file_path`, `source_series_instance_uid`:
  provenance columns linking back to the raw CBIS files.

### Possible Tasks

- Binary benign vs malignant classification using `is_malignant`.
- Multiclass pathology classification using `pathology`.
- Mass vs calcification classification using `abnormality_type`.
- Assessment prediction using `assessment`.
- Subgroup analysis using view, laterality, breast density, or abnormality type.

### Loading Example

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/CBIS-DDSM-clean")
labels = pd.read_csv(root / "labels.csv")
image = Image.open(root / "images" / labels.loc[0, "image"])
```

## Español

### Descripción del Dataset

Esta carpeta contiene una versión simplificada de CBIS-DDSM preparada para el Medical AI Datathon. Incluye mamografías completas redimensionadas y un archivo compacto
`labels.csv`.

Dataset original: https://www.cancerimagingarchive.net/collection/cbis-ddsm/

### Estructura

```text
CBIS-DDSM-clean/
├── images/
├── labels.csv
└── README.md
```

La columna `image` contiene solo el nombre del archivo PNG dentro de `images/`.

### Archivos

- `images/`: mamografías completas redimensionadas en formato PNG.
- `labels.csv`: etiquetas y metadatos relevantes para las tareas.
- `README.md`: este archivo.

### Variables Principales

- `image`: nombre del archivo dentro de `images/`.
- `split`: partición train/test proveniente de los archivos originales de CBIS.
- `patient_id`: identificador del paciente.
- `left_or_right_breast`: lateralidad de la mama.
- `image_view`: vista mamográfica, por ejemplo CC o MLO.
- `abnormality_id`: identificador de la anormalidad dentro del caso.
- `abnormality_type`: masa o calcificación.
- `assessment`: puntuación tipo BI-RADS.
- `breast_density`: categoría de densidad mamaria.
- `pathology`: etiqueta patológica original.
- `is_malignant`: etiqueta binaria derivada de `pathology`.
- `subtlety`: puntuación de sutileza de la descripción original.
- `mass_shape`, `mass_margins`: descriptores específicos para masas.
- `calc_type`, `calc_distribution`: descriptores específicos para
  calcificaciones.
- `source_case_csv`, `source_image_file_path`, `source_series_instance_uid`:
  columnas de procedencia hacia los archivos crudos de CBIS.

### Tareas Posibles

- Clasificación binaria benigno vs maligno usando `is_malignant`.
- Clasificación multiclase de patología usando `pathology`.
- Clasificación masa vs calcificación usando `abnormality_type`.
- Predicción de `assessment`.
- Análisis por subgrupos usando vista, lateralidad, densidad mamaria o tipo de
  anormalidad.

### Ejemplo de Lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/CBIS-DDSM-clean")
labels = pd.read_csv(root / "labels.csv")
image = Image.open(root / "images" / labels.loc[0, "image"])
```
