# CXR Report ES Challenge

## English

### Dataset Description

This private challenge dataset contains de-identified chest radiographs,
structured thoracic finding labels, study metadata, demographic variables, and
radiology reports in English and Spanish. Images are preprocessed chest X-rays
stored as JPG files.

The `report` column contains the original English radiology report. The
`report_spanish` column contains an automatic Spanish translation generated
with GPT-5 mini. Translations are intended to support multilingual clinical AI
research and challenge tasks; participants should evaluate translation quality
and clinical usability before relying on them as clinical text.

### Structure

After download and extraction, the dataset has this structure:

```text
CXR-Report-ES-Challenge/
├── images/
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

On Hugging Face, the image folder may be stored as `images.tar.gz` to make
download and upload practical. Extract it before loading images directly.

The `image` column contains only the image filename. To load an image, combine
the dataset path, `images/`, and the value in `image`.

### Files

- `images/` or `images.tar.gz`: chest X-ray JPG files.
- `train.csv`, `valid.csv`, `test.csv`: split files with image names, metadata,
  labels, English reports, and Spanish translated reports.
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
- `report`: original English radiology report text.
- `report_spanish`: automatic Spanish translation of `report`, generated with
  GPT-5 mini.

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

### Challenge Themes

This single dataset supports multiple challenge directions:

1. **Translation quality and clinical usability**: How should participants
   evaluate whether Spanish reports preserve the medical meaning of the English
   reports? Can participants improve translations using better
   prompting, image context, uncertainty-aware methods, or agentic pipelines?
2. **Metric design**: Are common text-generation metrics such as BLEU and ROUGE
   sufficient and scalable for clinical translation quality, or do they miss
   clinically important errors?
3. **Multilingual clinical AI**: Do models perform differently across English
   and Spanish reports?

### Possible Tasks

- Multi-label chest X-ray classification.
- Report-aware or multimodal modeling using `report` and `report_spanish`.
- Clinical translation evaluation and quality-control methods.
- Multilingual robustness, language bias, and fairness analysis.
- Methods for improving Spanish radiology report translation.

### Download

From Hugging Face:

```bash
pip install huggingface_hub
huggingface-cli download dsrestrepo/cxr-report-es-challenge \
  --repo-type dataset \
  --local-dir CXR-Report-ES-Challenge
```

If `images.tar.gz` is present:

```bash
tar -xzf CXR-Report-ES-Challenge/images.tar.gz \
  -C CXR-Report-ES-Challenge
```

Google Drive download example:
https://colab.research.google.com/drive/1m9TdSDnr0q64FMimAkM3kCKrBTP2PjjI?usp=sharing

Google Drive usage example:
https://colab.research.google.com/drive/18Pz47hpWzjlY1ujN5aWKinClyIicwfqX?usp=sharing

### Loading Example

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/CXR-Report-ES-Challenge")
metadata = pd.read_csv(root / "train.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])

english_report = metadata.loc[0, "report"]
spanish_report = metadata.loc[0, "report_spanish"]
```

## Español

### Descripción del Dataset

Este dataset privado de desafío contiene radiografías de tórax desidentificadas,
etiquetas estructuradas de hallazgos torácicos, metadatos del estudio,
variables demográficas y reportes radiológicos en inglés y español. Las
imágenes son radiografías de tórax preprocesadas en formato JPG.

La columna `report` contiene el reporte radiológico original en inglés. La
columna `report_spanish` contiene una traducción automática al español generada
con GPT-5 mini. Estas traducciones están pensadas para investigación en IA
clínica multilingüe y tareas de desafío; los participantes deben evaluar la
calidad de traducción y su utilidad clínica antes de depender de ellas como
texto clínico.

### Estructura

Después de descargar y extraer, el dataset tiene esta estructura:

```text
CXR-Report-ES-Challenge/
├── images/
├── train.csv
├── valid.csv
├── test.csv
└── README.md
```

En Hugging Face, la carpeta de imágenes puede estar guardada como
`images.tar.gz` para facilitar la descarga y subida. Extrae ese archivo antes
de cargar las imágenes directamente.

La columna `image` contiene solo el nombre del archivo. Para cargar una imagen,
combina la ruta del dataset, `images/` y el valor de `image`.

### Archivos

- `images/` o `images.tar.gz`: radiografías de tórax en formato JPG.
- `train.csv`, `valid.csv`, `test.csv`: archivos por split con nombres de
  imagen, metadatos, etiquetas, reportes en inglés y reportes traducidos al
  español.
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
- `report`: texto original del reporte radiológico en inglés.
- `report_spanish`: traducción automática al español de `report`, generada con
  GPT-5 mini.

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

### Ejes del Desafío

Este dataset permite varias líneas de desafío:

1. **Calidad de traducción y utilidad clínica**: ¿cómo evaluar si los reportes
   en español preservan el significado médico de los reportes en inglés? ¿Pueden los participantes mejorar las
   traducciones usando mejores prompts, contexto visual, manejo explícito de
   incertidumbre o pipelines agénticos?
2. **Diseño de métricas**: ¿son suficientes y escalables métricas como BLEU y
   ROUGE para evaluar traducción clínica, o pierden errores clínicamente
   importantes?
3. **IA clínica multilingüe**: ¿los modelos tienen diferente desempeño entre
   reportes en inglés y español?

### Tareas Posibles

- Clasificación multi-etiqueta de radiografías de tórax.
- Modelado multimodal o con reportes usando `report` y `report_spanish`.
- Evaluación y control de calidad de traducción clínica.
- Análisis de robustez multilingüe, sesgo lingüístico y equidad.
- Métodos para mejorar la traducción de reportes radiológicos al español.

### Descarga

Desde Hugging Face:

```bash
pip install huggingface_hub
huggingface-cli download dsrestrepo/cxr-report-es-challenge \
  --repo-type dataset \
  --local-dir CXR-Report-ES-Challenge
```

Si `images.tar.gz` está presente:

```bash
tar -xzf CXR-Report-ES-Challenge/images.tar.gz \
  -C CXR-Report-ES-Challenge
```

Ejemplo de descarga con Google Drive:
https://colab.research.google.com/drive/1m9TdSDnr0q64FMimAkM3kCKrBTP2PjjI?usp=sharing

Ejemplo de uso con Google Drive:
https://colab.research.google.com/drive/18Pz47hpWzjlY1ujN5aWKinClyIicwfqX?usp=sharing

### Ejemplo de Lectura

```python
from pathlib import Path
import pandas as pd
from PIL import Image

root = Path("PATH-TO-DATASET/CXR-Report-ES-Challenge")
metadata = pd.read_csv(root / "train.csv")
image = Image.open(root / "images" / metadata.loc[0, "image"])

report_en = metadata.loc[0, "report"]
report_es = metadata.loc[0, "report_spanish"]
```
