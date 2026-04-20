# UnibaBot PDA

Agente inteligente para la verificacion automatizada de Planes de Desarrollo Academico (PDA) de la Universidad de Ibague. El sistema recibe un PDA en formato PDF, lo evalua contra 179 lineamientos institucionales codificados, y genera un reporte estructurado de cumplimiento.

**Resultados sobre gold dataset expandido (112 entradas, 6 PDAs reales):**

| Split | Accuracy | Precision NC | Recall NC | Matched | Latencia |
|-------|----------|--------------|-----------|---------|----------|
| Train (57 entradas, 3 PDAs) | **0.965** | **1.000** | 0.500 | 57/57 | ~95s |
| Test hold-out (55 entradas, 3 PDAs nuevos) | **0.982** | 0.900 | **1.000** | 55/55 | ~120s |

*m13 extractor deterministico + Qwen 2.5 14B. NC = clase NO CUMPLE (incumplimientos reales). Train: PDAs vistos durante el desarrollo. Test: PDAs nunca tocados.*

## Contexto

Cada semestre, las oficinas de los programas academicos de la Universidad de Ibague deben verificar manualmente que mas de 20 PDAs cumplan con los lineamientos institucionales. Este proceso es lento, inconsistente y propenso a errores. UnibaBot PDA automatiza esta verificacion mediante un pipeline hibrido que combina verificacion rule-based determinista, despacho explicito de reglas por seccion, y extraccion de declaraciones con **Qwen 2.5 14B** corriendo localmente en un MacBook Pro M3 18GB.

## Arquitectura

```
PDF del PDA
    |
    v
[1. Extraccion + segmentacion]   src/pdf_parser.py
    |                            PyMuPDF + SECCIONES_CONOCIDAS bilingue
    v
[2. Rule-based estructural]      src/rules/estructural_checker.py
    |                            11 checkers deterministicos (EST-001..011)
    |                            100% precision en reglas estructurales
    v
[3. Despacho de reglas]          src/rag/rule_dispatcher.py
    |                            Mapea 168 reglas (reglas.json) a secciones del PDA
    |                            Match por nombre de seccion + fallback por keywords
    v
[4. Extraccion de declaraciones] src/rules/declaracion_extractor.py
    |                            1 llamada LLM por PDA (Qwen 2.5 14B)
    |                            Extrae codigos canonicos (C1, 1b, SP5, D4, ABET X.Y)
    |                            src/prompts/extraccion_prompt.txt
    v
[5. Matcher deterministico]      src/rules/declaracion_checker.py
    |                            Regex por tipo + set intersection
    |                            Compliance 100% reproducible y auditable
    v
[6. Reporte estructurado]        results/reports_<tag>.json
                                 regla_id / estado / evidencia / correccion
```

**Evolucion de resultados — hitos principales:**

| Hito | Descripcion | Accuracy | Prec NC | Recall NC | Matched | Latencia |
|------|-------------|----------|---------|-----------|---------|----------|
| baseline | Llama 3.2 3B sin mejoras (gold 48) | 0.351 | 0.000 | 0.000 | 37/48 | 565s |
| m8b | Pipeline RAG+LLM completo (Llama 3.1 8B, gold 48) | 1.000* | 1.000 | 1.000 | 45/48 | 236s |
| m11 | Rule-driven: 100% cobertura (gold 57+55) | 0.895 / 0.873 | 0.625 / 0.818 | 0.625 / 0.857 | 57/57 + 55/55 | 213s / 249s |
| m12 | Qwen 2.5 14B como modelo LLM (gold 57+55) | 0.930 / 0.891 | 1.000 / 0.826 | 0.500 / 0.905 | 57/57 + 55/55 | 441s / 366s |
| **m13 Train** | **Extractor deterministico** | **0.965** | **1.000** | **0.500** | **57/57** | **~95s** |
| **m13 Test** | **Hold-out 3 PDAs nuevos** | **0.982** | **0.900** | **1.000** | **55/55** | **~120s** |

*m8b: accuracy 1.000 sobre 45/48 entradas matcheadas, 3 excluidas por retrieval semantico. El salto de m8b a m11 no es una regresion: m11 introdujo evaluacion 100% deterministica revelando incumplimientos que el retrieval semantico omitia por no recuperarlos en el top-k.*

Ver [results/evaluation_report.md](results/evaluation_report.md) y [results/accuracy_progression.md](results/accuracy_progression.md) para el detalle completo por iteracion.

## Estructura del proyecto

```
Unibabot_PDA/
  src/
    pdf_parser.py                # Extraccion y segmentacion de PDAs
    agent.py                     # Pipeline completo del agente
    evaluate.py                  # Evaluacion contra gold dataset (train/test)
    generar_reglas.py            # Genera reglas desde JSON_archives/
    schemas.py                   # Modelos Pydantic para validacion estricta
    prompts/
      extraccion_prompt.txt      # Prompt de extraccion de codigos declarados (m13)
      compliance_prompt.txt      # Prompt de evaluacion LLM (fallback legacy)
      retry_prompt.txt           # Prompt de retry para JSON invalido
    rules/
      estructural_checker.py     # 11 checkers rule-based (EST-001..011)
      declaracion_extractor.py   # Extractor LLM de codigos canonicos (m13)
      declaracion_checker.py     # Matcher deterministico (m13)
    rag/
      rule_dispatcher.py         # Despacho de reglas a secciones del PDA (m11)
      seccion_mapping.py         # Mapping keyword_parser -> [seccion_pda]
      ingest.py                  # Carga reglas en ChromaDB (opt-in)
      retriever.py               # Busqueda semantica (opt-in, no es el default)
      embeddings.py              # SBERT custom embedding function (opt-in)
      reranker.py                # Cross-encoder reranker (opt-in)
    fine_tuning/
      prepare_dataset.py         # Genera pares instruccion-respuesta
      generar_outputs.py         # Genera outputs con Llama 3.2
    tooling/
      generar_gold_exhaustivo.py # Pipeline de generacion del gold dataset
      anotar_claude_train.py     # Anotacion Claude para split de train
      anotar_claude_test.py      # Anotacion Claude para split de test
      fusionar_gold.py           # Fusion de candidatos nuevos con gold existente
      limpiar_gold_modelos.py    # Elimina entradas huerfanas del gold
      corregir_gold_contra_pda.py# Correccion determinista de gold mal etiquetado
  data/
    lineamientos/
      reglas.json                # 179 reglas codificadas (11 EST + 168 COMP)
    gold_labels.json             # Gold dataset train (57 entradas, 3 PDAs)
    gold_labels_test.json        # Gold dataset test hold-out (55 entradas, 3 PDAs)
    chroma_db/                   # Base vectorial persistida (gitignored, opt-in)
    training_dataset.jsonl       # 42 ejemplos de entrenamiento (fine-tuning v1)
    validation_dataset.jsonl     # 5 ejemplos de validacion
  models/
    unibabot-pda.gguf            # Fine-tuned v1 (descartado, artefacto historico)
  notebooks/
    fine_tuning.ipynb            # Notebook para Google Colab (QLoRA)
  results/
    evaluation_report.md         # Reporte completo con metricas por iteracion (m1-m13)
    accuracy_progression.md      # Tabla de progresion de accuracy (m1-m13)
    metrics_<tag>.json           # Metricas por snapshot (gitignored)
    reports_<tag>.json           # Reportes crudos del agente (gitignored)
  PDAs/                          # PDAs reales en PDF (6 documentos, gitignored)
  JSON_archives/                 # Datos institucionales (ABET, competencias, cursos)
  Docs/                          # Documentacion tecnica y academica
    ARCHITECTURE.md              # Arquitectura tecnica del sistema (m13)
    EXPLICACION_TECNICA.md       # Documentacion exhaustiva para presentacion
  streamlit_app.py               # Interfaz web (Streamlit)
  webapp/                        # Componentes adicionales de la UI web
  ROADMAP.md                     # Plan de implementacion historico
  CLAUDE.md                      # Instrucciones del proyecto
  requirements.txt               # Dependencias Python
```

## Requisitos

- Python 3.12+
- **ollama** con Qwen 2.5 14B (default) y/o Llama 3.1 8B (comparativo)
- MacBook Pro M3 18GB o equivalente (Qwen 2.5 14B requiere ~9GB de VRAM)
- Google Colab con GPU T4 (solo si se quiere re-intentar fine-tuning con QLoRA)

## Instalacion

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd Unibabot_PDA

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Instalar y configurar ollama
brew install ollama
brew services start ollama
ollama pull qwen2.5:14b      # modelo de produccion (default, ~9GB)
ollama pull llama3.1:8b      # comparativo legacy (opcional)
ollama pull llama3.2         # baseline original (opcional)

# Generar reglas e ingestar en ChromaDB (necesario para la UI y opt-in RAG)
python src/generar_reglas.py
python src/rag/ingest.py
```

## Uso

### Interfaz web (Streamlit)

```bash
streamlit run streamlit_app.py
```

Abre la UI en `http://localhost:8501`. El flujo es:

1. Subir un PDA en PDF, opcionalmente escribir el codigo del curso (ej: `22A14`) y elegir modelo.
2. Al pulsar "Analizar PDA" se ve el progreso en vivo seccion por seccion.
3. El reporte se muestra con metricas globales, tabs (Estructural / Por seccion / Resumen) y acordeones con badges coloreados por hallazgo.
4. Cada reporte se guarda automaticamente en `results/history/` y aparece en el sidebar para consultar despues sin re-analizar.

### Analizar un PDA (CLI)

```bash
# Default: usa Qwen 2.5 14B (m13, accuracy 0.982 en test hold-out)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14

# Con modelo explicito
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 qwen    # Qwen 2.5 14B (default)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 8b      # Llama 3.1 8B (legacy)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 baseline # Llama 3.2 3B (baseline)
```

El segundo argumento es el codigo del curso (opcional). Si se proporciona, el sistema filtra las reglas de competencias especificas de ese curso. El reporte se guarda en `results/reporte_<modelo>.json`.

### Evaluar contra gold dataset

```bash
# Evaluar train (3 PDAs originales, 57 entradas)
python src/evaluate.py --tag mi_experimento --modelo qwen2.5:14b

# Evaluar test hold-out (3 PDAs nuevos, 55 entradas)
python src/evaluate.py --gold-path data/gold_labels_test.json --tag mi_experimento_test --modelo qwen2.5:14b

# Comparar dos runs guardados
python src/evaluate.py --compare baseline mi_experimento

# Recalcular metricas de un run previo sin re-inferir
python src/evaluate.py --tag baseline --reuse
```

### Explorar un PDF

```bash
# Ver bloques crudos con metadata de fuente
python src/pdf_parser.py "../PDAs/tu_pda.pdf" --bloques

# Ver secciones segmentadas
python src/pdf_parser.py "../PDAs/tu_pda.pdf" --secciones
```

### Probar el retriever (opt-in, experimentos RAG)

```bash
python src/rag/retriever.py "resultados de aprendizaje" 22A14
```

### Fine-tuning (Google Colab)

1. Abrir `notebooks/fine_tuning.ipynb` en Google Colab
2. Seleccionar Runtime -> Change runtime type -> GPU T4
3. Subir `data/training_dataset.jsonl` y `data/validation_dataset.jsonl`
4. Ejecutar todas las celdas en orden
5. Descargar el modelo GGUF generado

### Registrar modelo fine-tuneado en ollama

```bash
cat > Modelfile << 'EOF'
FROM ./llama-3.2-3b-instruct.Q4_K_M.gguf
PARAMETER temperature 0.1
SYSTEM Eres un evaluador academico de la Universidad de Ibague que verifica el cumplimiento de Planes de Desarrollo Academico (PDA).
EOF

ollama create unibabot-pda -f Modelfile
```

## Base de conocimiento

Las 179 reglas se generan automaticamente cruzando los datos de `JSON_archives/`:

| Fuente | Contenido |
|--------|-----------|
| `cursos.json` | Catalogo de 23 materias (codigo, nombre, semestre) |
| `competenciascursos.json` | Competencias requeridas por materia |
| `competencias.json` | Descripcion de competencias especificas, genericas, SABER PRO, dimensiones |
| `abet.json` / `abet_es.json` | Indicadores ABET en ingles y espanol |

Tipos de reglas generadas:

| Tipo | Cantidad | Ejemplo |
|------|----------|---------|
| Estructural | 11 | "Todo PDA debe incluir bibliografia de referencia" |
| Competencia especifica | 32 | "El PDA de Agentes Inteligentes debe declarar C1" |
| Competencia generica | 61 | "Debe declarar competencia 1c: Comunicacion en segunda lengua" |
| SABER PRO | 24 | "Debe declarar SP5: Ingles" |
| ABET | 36 | "Debe cubrir indicador 1.1: Analiza un problema de ingenieria..." |
| Dimension | 15 | "Debe declarar dimension D4: Internacional" |

## Fine-tuning (artefacto historico)

El fine-tuning con QLoRA fue la primera estrategia explorada (m7). El modelo fine-tuneado entro en loops de generacion y fue descartado. Las mejoras sistematicas de ingenieria del pipeline (m8-m13) superaron con creces los resultados del fine-tuning sin sus riesgos.

| Parametro | Valor |
|-----------|-------|
| Modelo base | Llama 3.2 3B Instruct |
| Tecnica | QLoRA (4-bit NF4 + LoRA r=16) |
| Dataset | 42 train + 5 validation (formato Alpaca) |
| Epochs | 3 |
| Learning rate | 2e-4 |
| Batch size efectivo | 8 (2 x 4 gradient accumulation) |
| Hardware | Google Colab T4 (16GB VRAM) |
| Resultado | Train loss 1.64 -> 1.26, Val loss 1.52 -> 1.15 (pero loops en inferencia) |

## Decisiones tecnicas clave

1. **LLM para extraccion, no para razonamiento:** El LLM es fuerte extrayendo codigos ("C1", "SP5") de texto, pero debil razonando si una declaracion informal cumple una regla formal. m13 separa los dos roles: LLM extrae, codigo Python decide.

2. **Rule-driven vs retrieval-driven:** m11 invirtio el flujo. En vez de "busca semanticamente las reglas mas similares al texto", el sistema ahora "para cada regla aplicable al curso, encuentra la seccion del PDA donde debe declararse". Esto garantiza cobertura 100%.

3. **Determinismo en compliance:** El veredicto final de cumplimiento es 100% reproducible (regex + set intersection). Solo la fase de extraccion tiene estocasticidad.

4. **Infraestructura RAG como opt-in:** ChromaDB, SBERT multilingue y cross-encoder reranker (m9) existen en el codigo pero no son el pipeline de produccion. Se pueden activar con variables de entorno para experimentacion.

5. **Gold dataset como evidencia de generalizacion:** El test hold-out con 3 PDAs nunca vistos durante el desarrollo (accuracy 0.982) demuestra que el sistema no memoriza patrones de los PDAs de entrenamiento.

## Limitaciones identificadas

1. **Recall NC en train = 0.500:** El extractor ocasionalmente no detecta declaraciones semanticamente correctas pero con formulacion inusual (ej: "vision sistemica" en lugar del codigo "1h: Pensamiento critico").
2. **1 FP residual en test:** Un caso edge donde el extractor sobre-detecta D4 en Agentes Inteligentes por la frase "international dimension integrated".
3. **Parser dependiente del formato PDF:** PDAs con tablas complejas o escaneados como imagen pueden no segmentarse correctamente.
4. **Dataset de 6 PDAs:** Mas PDAs (20+) permitirian metricas estadisticamente mas robustas para la clase NC.

## Autores

- Kevin Beltran Martinez (2220221003)
- Jeryleefth Lasso Motta (2220231074)

Ingenieria de Sistemas, Universidad de Ibague, 2026A
Asignatura: Agentes Inteligentes
