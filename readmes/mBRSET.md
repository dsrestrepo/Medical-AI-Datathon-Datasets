# mBRSET Clean Dataset / Dataset limpio mBRSET

## English

### Dataset Description

This folder contains a clean mBRSET subset prepared for the Medical AI Datathon. Images are
retinal fundus photographs stored as JPG files. `metadata.csv` includes one row
per image, with patient-level clinical variables, demographic variables, image
quality fields, and retinal labels.

Original dataset: https://physionet.org/content/mbrset/

### Structure

```text
mBRSET/
├── images/
├── metadata.csv
└── README.md
```

The `image` column contains only the image filename.

### Files

- `images/`: retinal fundus JPG images.
- `metadata.csv`: image metadata, labels, clinical variables, and split.
- `README.md`: this file.

### Main Variables

- `image`: image filename inside `images/`.
- `split`: train/validation/test split.
- `patient`: patient identifier.
- `age`, `sex`: demographic variables.
- `laterality`: eye laterality.
- `final_icdr`: diabetic retinopathy severity grade using ICDR scale.
- `final_edema`: edema label.
- `increased_cdr`: increased cup-to-disc ratio, related to glaucoma screening.
- `final_quality`, `final_artifacts`: image quality and artifacts.
- `dm_time`, `insulin`, `insulin_time`, `oraltreatment_dm`: diabetes history
  and treatment variables.
- `systemic_hypertension`, `obesity`, `vascular_disease`,
  `acute_myocardial_infarction`, `nephropathy`, `neuropathy`,
  `diabetic_foot`: clinical comorbidities.
- `insurance`, `educational_level`, `alcohol_consumption`, `smoking`:
  demographic and lifestyle variables.

### Possible Tasks

- Diabetic retinopathy severity prediction using `final_icdr`.
- Edema prediction using `final_edema`.
- Glaucoma-related screening using `increased_cdr`.
- Image quality prediction using `final_quality`.
- Subgroup, robustness, or fairness analysis using clinical and demographic
  variables.

### Loading Example

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/mBRSET")
metadata = pd.read_csv(root / "metadata.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])
```

## Español

### Descripción del Dataset

Esta carpeta contiene un subconjunto limpio de mBRSET preparado para el Medical AI Datathon. Las imágenes son fotografías de fondo de ojo en formato JPG.
`metadata.csv` incluye una fila por imagen, con variables clínicas del paciente,
variables demográficas, campos de calidad de imagen y etiquetas retinianas.

Dataset original: https://physionet.org/content/mbrset/

### Estructura

```text
mBRSET/
├── images/
├── metadata.csv
└── README.md
```

La columna `image` contiene solo el nombre del archivo.

### Archivos

- `images/`: imágenes de fondo de ojo en formato JPG.
- `metadata.csv`: metadatos, etiquetas, variables clínicas y split.
- `README.md`: este archivo.

### Variables Principales

- `image`: nombre del archivo dentro de `images/`.
- `split`: partición train/valid/test.
- `patient`: identificador del paciente.
- `age`, `sex`: variables demográficas.
- `laterality`: lateralidad del ojo.
- `final_icdr`: severidad de retinopatía diabética según escala ICDR.
- `final_edema`: etiqueta de edema.
- `increased_cdr`: relación copa-disco aumentada, relacionada con tamizaje de
  glaucoma.
- `final_quality`, `final_artifacts`: calidad y artefactos de la imagen.
- `dm_time`, `insulin`, `insulin_time`, `oraltreatment_dm`: historia y
  tratamiento de diabetes.
- `systemic_hypertension`, `obesity`, `vascular_disease`,
  `acute_myocardial_infarction`, `nephropathy`, `neuropathy`,
  `diabetic_foot`: comorbilidades clínicas.
- `insurance`, `educational_level`, `alcohol_consumption`, `smoking`:
  variables demográficas y de estilo de vida.

### Tareas Posibles

- Predicción de severidad de retinopatía diabética usando `final_icdr`.
- Predicción de edema usando `final_edema`.
- Tamizaje relacionado con glaucoma usando `increased_cdr`.
- Predicción de calidad de imagen usando `final_quality`.
- Análisis por subgrupos, robustez o equidad usando variables clínicas y
  demográficas.

### Ejemplo de Lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/mBRSET")
metadata = pd.read_csv(root / "metadata.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])
```
