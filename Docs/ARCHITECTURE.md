# Arquitectura de UnibaBot PDA

## Vision general

UnibaBot PDA es un agente inteligente que implementa un pipeline de verificacion de cumplimiento normativo. El sistema combina dos tecnicas de NLP: RAG (Retrieval-Augmented Generation) para recuperar lineamientos relevantes, y fine-tuning con QLoRA para especializar un modelo de lenguaje en la tarea de evaluacion.

## Componentes del sistema

### 1. PDF Parser (`src/pdf_parser.py`)

**Responsabilidad:** Convertir un PDA en PDF a un diccionario de secciones segmentadas.

**Flujo interno:**
```
PDF -> fitz.open() -> paginas -> bloques -> spans -> metadata
    -> extraer_bloques() -> lista de {text, page, font_size, is_bold}
    -> segmentar_por_secciones() -> {nombre_seccion: contenido}
```

**Decisiones de diseno:**

- Se usa PyMuPDF (`fitz`) con modo `"dict"` para obtener metadata de fuente (tamano, bold), no solo texto plano. Esto permite distinguir encabezados de contenido.
- La deteccion de encabezados usa un **doble filtro**: el bloque debe parecer un encabezado visualmente (fuente grande o bold) Y debe matchear alguna seccion de `SECCIONES_CONOCIDAS`.
- `SECCIONES_CONOCIDAS` es una lista bilingue (espanol/ingles) con normalizacion de acentos para tolerar variaciones en los PDAs.
- La funcion `normalizar()` quita acentos, numeros de seccion y pasa a minusculas para comparacion flexible.

**Limitaciones conocidas:**
- PDAs con tablas complejas pueden generar bloques fragmentados
- Algunos campos de tabla (bold y cortos) pasan el filtro si coinciden con secciones conocidas
- No soporta PDAs escaneados como imagen (requeriria OCR)

### 2. Sistema RAG (`src/rag/`)

**Responsabilidad:** Dado un fragmento de texto del PDA, recuperar los lineamientos institucionales mas relevantes.

#### Ingesta (`ingest.py`)

```
reglas.json -> 179 documentos con metadata -> ChromaDB (cosine similarity)
```

- Cada regla es un documento independiente en ChromaDB
- Metadata por regla: `tipo`, `seccion_pda`, `aplica_a`
- ChromaDB usa su modelo de embeddings por defecto (`all-MiniLM-L6-v2` via ONNX)
- La base se persiste en `data/chroma_db/`

#### Retriever (`retriever.py`)

```
recuperar_lineamientos(texto, top_k=5, codigo_curso=None)
    -> query a ChromaDB con filtro opcional
    -> lista de {descripcion, tipo, distancia}
```

- Si se proporciona `codigo_curso`, filtra con `$or`: reglas del curso + reglas de "todos"
- Sin codigo de curso, busca en todas las 179 reglas
- Distancia coseno: 0 = identico, 2 = opuesto

**Decisiones de diseno:**
- `top_k=5` por defecto para limitar contexto en un modelo de 3B parametros
- ChromaDB se eligio por simplicidad (pip install, sin servidor, persistencia en disco)
- Las reglas estructurales tienden a dominar el top-5 porque su texto es mas generico

### 3. Generador de reglas (`src/generar_reglas.py`)

**Responsabilidad:** Cruzar los datos de `JSON_archives/` para producir `data/lineamientos/reglas.json`.

**Fuentes de datos:**
```
cursos.json              -> codigo a nombre de materia
competenciascursos.json  -> que competencias requiere cada materia
competencias.json        -> descripcion de cada competencia
abet_es.json             -> indicadores ABET en espanol
```

**Tipos de reglas:**
- **Estructurales (11):** Secciones obligatorias en todo PDA, definidas manualmente
- **De competencias (168):** Generadas automaticamente por cada par (curso, competencia requerida)

### 4. Agente (`src/agent.py`)

**Responsabilidad:** Orquestar el pipeline completo de evaluacion.

**Pipeline:**
```
1. parsear_pda(pdf_path)          -> {seccion: contenido}
2. preparar_evaluacion(secciones) -> filtra secciones + recupera lineamientos
3. evaluar_seccion() x N          -> prompt + LLM -> JSON con hallazgos
4. Reporte consolidado            -> results/reporte_cumplimiento.json
```

**Decisiones de diseno:**
- El contenido se trunca a 2000 caracteres por seccion para no exceder la ventana de contexto del modelo 3B
- Temperatura 0.1 para respuestas deterministas
- Parsing de JSON tolerante: busca `{` y `}` en la respuesta para extraer el JSON aunque el LLM agregue texto extra
- Si el JSON no es parseable, se devuelve la respuesta cruda con flag de error

### 5. Prompt de evaluacion (`src/prompts/compliance_prompt.txt`)

**Estructura:**
```
[Rol]       Evaluador academico de la Universidad de Ibague
[Contexto]  Seccion del PDA + contenido
[Reglas]    Lineamientos recuperados por RAG
[Formato]   JSON con hallazgos (regla, estado, evidencia, correccion)
```

Las llaves dobles `{{` `}}` son escape de Python `.format()`, no parte del JSON.

### 6. Fine-tuning (`src/fine_tuning/`, `notebooks/`)

**Pipeline de datos:**
```
4 PDAs reales
    -> prepare_dataset.py   -> 47 pares (instruction, input, output="")
    -> generar_outputs.py   -> outputs generados por Llama 3.2
    -> training_dataset.jsonl (42) + validation_dataset.jsonl (5)
```

**Entrenamiento:**
```
Llama 3.2 3B Instruct
    -> cuantizacion 4-bit NF4 (Unsloth)
    -> adaptadores LoRA (r=16, alpha=16, 7 target modules)
    -> SFTTrainer (3 epochs, lr=2e-4, batch=8 efectivo)
    -> adaptador LoRA (~50MB) o GGUF Q4_K_M (~2GB)
```

## Flujo de datos

```
JSON_archives/          src/generar_reglas.py
  abet.json        ---->    |
  abet_es.json     ---->    |
  competencias.json ---->   v
  competenciascursos.json -> data/lineamientos/reglas.json
  cursos.json      ---->                |
                                        v
                              src/rag/ingest.py
                                        |
                                        v
                              data/chroma_db/ (ChromaDB)
                                        |
PDAs/*.pdf                              |
    |                                   |
    v                                   v
src/pdf_parser.py          src/rag/retriever.py
    |                                   |
    v                                   v
{secciones}  +  {lineamientos}  ->  src/agent.py
                                        |
                                        v
                              results/reporte_cumplimiento.json
```

## Dependencias externas

| Dependencia | Version | Proposito |
|-------------|---------|-----------|
| PyMuPDF (fitz) | >=1.24.0 | Extraccion de texto y metadata de PDF |
| ChromaDB | >=0.5.0 | Base de datos vectorial para lineamientos |
| sentence-transformers | >=3.0.0 | Modelos de embeddings (dependencia de ChromaDB) |
| ollama | >=0.3.0 | Cliente Python para inferencia con Llama 3.2 |
| Unsloth | (Colab) | Fine-tuning acelerado con QLoRA |

## Consideraciones de rendimiento

- **Extraccion de PDF:** ~1 segundo por PDA (4-8 paginas)
- **Retrieval:** ~100ms por query a ChromaDB (179 documentos)
- **Inferencia LLM:** ~10-30 segundos por seccion en MacBook Pro M3
- **Pipeline completo:** ~3-5 minutos por PDA (14 secciones promedio)
- **Fine-tuning:** ~5 minutos en Google Colab T4

## Posibles mejoras futuras

- Soportar PDAs escaneados como imagen (OCR con Tesseract)
- Agregar validacion cruzada entre secciones (ej: verificar que las competencias declaradas en "Informacion general" se reflejen en los RAEs)
- Interfaz web para subir PDAs y visualizar reportes
- Ampliar dataset de fine-tuning con mas PDAs de otros programas
- Evaluar modelos alternativos (Mistral, Gemma) como base para fine-tuning
