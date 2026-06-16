# Medical AI Datathon

<p align="center">
  <img src="logo/logo.png" alt="Medical AI Datathon logo" width="280">
</p>

## English

This repository contains the code used to download, clean, and preprocess the
medical imaging datasets prepared for the Medical AI Datathon. The goal is to
provide participant-friendly datasets with simple file structures,
metadata/label CSV files, and example notebooks showing how to load and inspect
the data. The collection is broad enough to be reused in future medical AI
datathons or educational challenges.

The datasets are available in the Hugging Face collection:
https://huggingface.co/collections/dsrestrepo/medical-ai-datathon

The repository contains preprocessing code for four datasets:

- **MIMIC-CXR**: chest X-ray images with multi-label thoracic findings and
  radiology reports.
- **mBRSET**: retinal fundus images with ophthalmology labels, clinical
  variables, and demographic metadata.
- **CBIS-DDSM**: mammography images with breast lesion labels and case
  metadata.
- **LIDC-IDRI**: 3D chest CT volumes with radiologist annotations for lung
  nodules.

For more details about each dataset, participants should check the original
dataset sources/papers and the `README.md` file inside each clean dataset
folder.

### Clean Dataset Folders

The clean datasets are expected under a root folder such as:

```text
PATH-TO-DATASET/
```

#### MIMIC-CXR

```text
PATH-TO-DATASET/MIMIC-CXR/
├── images/
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

Contains 224x224 chest X-ray JPG images. The CSV files include image names,
study metadata, demographic variables, CheXpert-style labels, and the
`report` text.

Possible tasks:

- Multi-label chest X-ray classification.
- Report-aware or multimodal modeling.
- Subgroup or fairness analysis using metadata.

Original sources:

- Paper: https://www.nature.com/articles/s41597-019-0322-0
- Dataset: https://physionet.org/content/mimic-cxr/

#### mBRSET

```text
PATH-TO-DATASET/mBRSET/
├── images/
├── metadata.csv
└── README.md
```

Contains retinal fundus JPG images. `metadata.csv` includes one row per image
with clinical variables, demographic variables, image quality fields, and
retinal labels.

Possible tasks:

- Diabetic retinopathy severity prediction using `final_icdr`.
- Edema prediction using `final_edema`.
- Glaucoma-related screening using `increased_cdr`.
- Subgroup, robustness, or fairness analysis.

Original sources:

- Paper: https://www.nature.com/articles/s41597-025-04627-3
- Dataset: https://physionet.org/content/mbrset/

#### CBIS-DDSM

```text
PATH-TO-DATASET/CBIS-DDSM-clean/
├── images/
├── labels.csv
└── README.md
```

Contains resized full mammogram PNG images. `labels.csv` includes image names,
pathology labels, breast-view metadata, abnormality descriptors, and a binary
`is_malignant` label.

Possible tasks:

- Binary benign vs malignant classification using `is_malignant`.
- Multiclass pathology classification using `pathology`.
- Mass vs calcification classification using `abnormality_type`.
- Assessment prediction or subgroup analysis.

Original source: https://www.cancerimagingarchive.net/collection/cbis-ddsm/

#### LIDC-IDRI

```text
PATH-TO-DATASET/LIDC-IDRI-clean-224/
├── volumes/
├── reader_level.csv
├── nodule_level.csv
├── ct_level.csv
├── preprocessing_summary.json
└── README.md
```

An optional higher-resolution version can also be created:

```text
PATH-TO-DATASET/LIDC-IDRI-clean-384/
```

Contains 3D CT volumes stored as compressed `.npz` files. Each volume has shape
`(height, width, slices)`. Labels are available at reader/annotation level,
approximate nodule level, and derived CT-scan level.

Possible tasks:

- CT-level suspicious nodule or malignancy-risk classification using
  `has_malignant_or_high_suspicion`.
- CT-level multiclass classification using `ct_malignancy_class`.
- Reader-level or nodule-level analysis using the additional CSV files.

Original source: https://www.cancerimagingarchive.net/collection/lidc-idri/

### Notebooks

Each clean dataset has a simple notebook in `datathon/notebooks/` showing how
to read the labels, inspect columns, summarize labels, and visualize images or
CT volumes:

```text
datathon/notebooks/01_mimic_cxr_overview.ipynb
datathon/notebooks/02_mbrset_overview.ipynb
datathon/notebooks/03_cbis_ddsm_overview.ipynb
datathon/notebooks/04_lidc_idri_overview.ipynb
```

### Reproducibility

The `jobs/` and `scripts/` folders contain the Slurm jobs and Python scripts
used to download and preprocess the datasets. Participants do not need to run
these scripts to use the clean datasets, but they are included for transparency
and reproducibility.

## Español

Este repositorio contiene el código usado para descargar, limpiar y preprocesar los
datasets de imágenes médicas preparados para el Medical AI Datathon. El objetivo
es entregar datasets fáciles de usar, con estructuras simples, archivos CSV de
metadatos/etiquetas y notebooks de ejemplo para cargar e inspeccionar los datos.
La colección es suficientemente general para reutilizarse en futuros datathons
de IA médica o retos educativos.

Los datasets están disponibles en la colección de Hugging Face:
https://huggingface.co/collections/dsrestrepo/medical-ai-datathon

El repositorio contiene código de preprocesamiento para cuatro datasets:

- **MIMIC-CXR**: radiografías de tórax con etiquetas multi-etiqueta de hallazgos
  torácicos y reportes radiológicos.
- **mBRSET**: imágenes de fondo de ojo con etiquetas oftalmológicas, variables
  clínicas y metadatos demográficos.
- **CBIS-DDSM**: mamografías con etiquetas de lesiones mamarias y metadatos de
  casos.
- **LIDC-IDRI**: volúmenes CT 3D de tórax con anotaciones de radiólogos para
  nódulos pulmonares.

Para más información sobre cada dataset, los participantes pueden consultar las
fuentes/papers originales y el archivo `README.md` dentro de cada carpeta limpia
del dataset.

### Carpetas Limpias de Datasets

Los datasets limpios se esperan bajo una carpeta raíz como:

```text
PATH-TO-DATASET/
```

#### MIMIC-CXR

```text
PATH-TO-DATASET/MIMIC-CXR/
├── images/
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

Contiene radiografías de tórax JPG de 224x224. Los CSV incluyen nombres de
imagen, metadatos del estudio, variables demográficas, etiquetas tipo CheXpert y
el texto del `report`.

Tareas posibles:

- Clasificación multi-etiqueta de radiografías de tórax.
- Modelado multimodal o con reportes.
- Análisis por subgrupos o equidad usando metadatos.

Fuentes originales:

- Paper: https://www.nature.com/articles/s41597-019-0322-0
- Dataset: https://physionet.org/content/mimic-cxr/

#### mBRSET

```text
PATH-TO-DATASET/mBRSET/
├── images/
├── metadata.csv
└── README.md
```

Contiene imágenes JPG de fondo de ojo. `metadata.csv` incluye una fila por
imagen con variables clínicas, variables demográficas, campos de calidad de
imagen y etiquetas retinianas.

Tareas posibles:

- Predicción de severidad de retinopatía diabética usando `final_icdr`.
- Predicción de edema usando `final_edema`.
- Tamizaje relacionado con glaucoma usando `increased_cdr`.
- Análisis por subgrupos, robustez o equidad.

Fuentes originales:

- Paper: https://www.nature.com/articles/s41597-025-04627-3
- Dataset: https://physionet.org/content/mbrset/

#### CBIS-DDSM

```text
PATH-TO-DATASET/CBIS-DDSM-clean/
├── images/
├── labels.csv
└── README.md
```

Contiene mamografías completas redimensionadas en formato PNG. `labels.csv`
incluye nombres de imagen, etiquetas patológicas, metadatos de vista mamaria,
descriptores de anormalidades y una etiqueta binaria `is_malignant`.

Tareas posibles:

- Clasificación binaria benigno vs maligno usando `is_malignant`.
- Clasificación multiclase de patología usando `pathology`.
- Clasificación masa vs calcificación usando `abnormality_type`.
- Predicción de assessment o análisis por subgrupos.

Fuente original: https://www.cancerimagingarchive.net/collection/cbis-ddsm/

#### LIDC-IDRI

```text
PATH-TO-DATASET/LIDC-IDRI-clean-224/
├── volumes/
├── reader_level.csv
├── nodule_level.csv
├── ct_level.csv
├── preprocessing_summary.json
└── README.md
```

También puede crearse una versión opcional de mayor resolución:

```text
PATH-TO-DATASET/LIDC-IDRI-clean-384/
```

Contiene volúmenes CT 3D guardados como archivos `.npz` comprimidos. Cada
volumen tiene forma `(height, width, slices)`. Las etiquetas están disponibles
a nivel de lector/anotación, nivel aproximado de nódulo y nivel CT derivado.

Tareas posibles:

- Clasificación CT-level de sospecha de nódulo o riesgo de malignidad usando
  `has_malignant_or_high_suspicion`.
- Clasificación multiclase CT-level usando `ct_malignancy_class`.
- Análisis a nivel de lector o nódulo usando los CSV adicionales.

Fuente original: https://www.cancerimagingarchive.net/collection/lidc-idri/

### Notebooks

Cada dataset limpio tiene un notebook sencillo en `datathon/notebooks/` que
muestra cómo leer las etiquetas, inspeccionar columnas, resumir etiquetas y
visualizar imágenes o volúmenes CT:

```text
datathon/notebooks/01_mimic_cxr_overview.ipynb
datathon/notebooks/02_mbrset_overview.ipynb
datathon/notebooks/03_cbis_ddsm_overview.ipynb
datathon/notebooks/04_lidc_idri_overview.ipynb
```

### Reproducibilidad

Las carpetas `jobs/` y `scripts/` contienen los jobs de Slurm y scripts de
Python usados para descargar y preprocesar los datasets. Los participantes no
necesitan ejecutar estos scripts para usar los datasets limpios, pero se
incluyen por transparencia y reproducibilidad.
