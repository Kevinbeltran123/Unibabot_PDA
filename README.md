# UnibaBot PDA

Agente inteligente para la verificacion automatizada de Planes de Desarrollo Academico (PDA) de la Universidad de Ibague. El sistema recibe un PDA en formato PDF, lo evalua contra 179 lineamientos institucionales codificados, y genera un reporte estructurado de cumplimiento.

**Accuracy sobre gold dataset:** 1.000 (sistema final tras 5 mejoras mergeadas + 2 descartadas como experimentos negativos)

## Contexto

Cada semestre, las oficinas de los programas academicos de la Universidad de Ibague deben verificar manualmente que mas de 20 PDAs cumplan con los lineamientos institucionales. Este proceso es lento, inconsistente y propenso a errores. UnibaBot PDA automatiza esta verificacion mediante un pipeline hibrido que combina verificacion rule-based determinista, busqueda semantica filtrada (RAG), y un modelo de lenguaje Llama 3.1 8B corriendo localmente en un MacBook Pro M3 18GB.

## Arquitectura

```
PDF del PDA
    |
    v
[1. Extraccion + segmentacion]   src/pdf_parser.py
    |                            PyMuPDF + SECCIONES_CONOCIDAS bilingue
    v
[2. Rule-based determinista]     src/rules/estructural_checker.py
    |                            11 checkers (EST-001 a EST-011)
    |                            100% precision en reglas estructurales
    v
[3. RAG con filtro por seccion]  src/rag/retriever.py + seccion_mapping.py
    |                            ChromaDB + filtro aplica_a + filtro seccion_pda
    |                            179 reglas, ~5 relevantes por seccion
    v
[4. Prompt con few-shot]         src/prompts/compliance_prompt.txt
    |                            3 ejemplos (2 CUMPLE + 1 NO CUMPLE)
    v
[5. LLM + validacion Pydantic]   src/agent.py + src/schemas.py
    |                            Llama 3.1 8B via ollama
    |                            Retry automatico si JSON invalido
    v
[6. Reporte estructurado]        results/reports_<tag>.json
                                 regla_id / estado / evidencia / correccion
```

**Resultados sobre gold dataset de 48 entradas etiquetadas:**

| Metrica | Baseline (Llama 3.2 3B) | Final (pipeline completo) |
|---------|--------------------------|---------------------------|
| Accuracy | 0.351 | **1.000** |
| Precision NO CUMPLE | 0.000 | **1.000** |
| Recall NO CUMPLE | 0.000 | **1.000** |
| JSON valid rate | 0.986 | **1.000** |
| Latencia (4 PDAs) | 565s | 189s |

Ver [results/evaluation_report.md](results/evaluation_report.md) y [results/accuracy_progression.md](results/accuracy_progression.md) para el detalle por mejora.

## Estructura del proyecto

```
Unibabot_PDA/
  src/
    pdf_parser.py                # Extraccion y segmentacion de PDAs
    agent.py                     # Pipeline completo del agente
    evaluate.py                  # Script de medicion contra gold dataset
    generar_reglas.py            # Genera reglas desde JSON_archives/
    schemas.py                   # Modelos Pydantic para validacion estricta
    prompts/
      compliance_prompt.txt      # Prompt con 3 ejemplos few-shot
      retry_prompt.txt           # Prompt de retry si JSON invalido
    rag/
      ingest.py                  # Carga reglas en ChromaDB
      retriever.py               # Busqueda semantica con filtros
      seccion_mapping.py         # Mapping keyword_parser -> [seccion_pda]
    rules/
      estructural_checker.py     # 11 checkers rule-based (EST-001..011)
    fine_tuning/
      prepare_dataset.py         # Genera pares instruccion-respuesta
      generar_outputs.py         # Genera outputs con Llama 3.2
  data/
    lineamientos/
      reglas.json                # 179 reglas codificadas
    gold_labels.json             # Gold dataset (48 entradas etiquetadas)
    chroma_db/                   # Base vectorial persistida (gitignored)
    training_dataset.jsonl       # 42 ejemplos de entrenamiento (fine-tuning v1)
    validation_dataset.jsonl     # 5 ejemplos de validacion
  models/
    unibabot-pda.gguf            # Fine-tuned v1 (descartado, artefacto historico)
  notebooks/
    fine_tuning.ipynb            # Notebook para Google Colab (QLoRA)
  results/
    evaluation_report.md         # Reporte final con metricas completas
    accuracy_progression.md      # Tabla por mejora + analisis
    metrics_<tag>.json           # Metricas por snapshot (gitignored)
    reports_<tag>.json           # Reportes crudos del agente (gitignored)
  PDAs/                          # PDAs reales en PDF (4 documentos, gitignored)
  JSON_archives/                 # Datos institucionales (ABET, competencias)
  Docs/                          # Documentacion academica y presentaciones
  ROADMAP.md                     # Plan de implementacion por fases
  CLAUDE.md                      # Instrucciones del proyecto
  requirements.txt               # Dependencias Python
```

## Requisitos

- Python 3.12+
- ollama con Llama 3.1 8B (default) y/o Llama 3.2 3B (baseline comparativo)
- MacBook Pro M3 18GB o equivalente (para el 8B)
- Google Colab con GPU T4 (opcional, solo si se quiere re-intentar fine-tuning)

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
ollama pull llama3.1:8b      # modelo de produccion (default)
ollama pull llama3.2         # baseline para comparacion (opcional)

# Ingestar reglas en ChromaDB
python src/generar_reglas.py
python src/rag/ingest.py
```

## Uso

### Analizar un PDA

```bash
# Default: usa Llama 3.1 8B (accuracy 1.000 sobre gold)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14

# Con modelo explicito
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 baseline    # llama3.2 3B
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 8b          # llama3.1 8B
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 llama3.1:8b # nombre crudo
```

El segundo argumento es el codigo del curso (opcional). Si se proporciona, el sistema filtra las reglas de competencias especificas de ese curso. El reporte se guarda en `results/reporte_<modelo>.json`.

### Evaluar contra gold dataset

```bash
# Corre los 4 PDAs y calcula metricas contra data/gold_labels.json
python src/evaluate.py --tag mi_experimento --modelo llama3.1:8b

# Comparar dos runs guardados
python src/evaluate.py --compare baseline mi_experimento

# Recalcular metricas de un run previo sin re-inferir
python src/evaluate.py --tag baseline --reuse
```

### Explorar un PDF

```bash
# Ver bloques crudos con metadata
python src/pdf_parser.py "../PDAs/tu_pda.pdf" --bloques

# Ver secciones segmentadas
python src/pdf_parser.py "../PDAs/tu_pda.pdf" --secciones
```

### Probar el retriever

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
# Crear Modelfile
cat > Modelfile << 'EOF'
FROM ./llama-3.2-3b-instruct.Q4_K_M.gguf
PARAMETER temperature 0.1
SYSTEM Eres un evaluador academico de la Universidad de Ibague que verifica el cumplimiento de Planes de Desarrollo Academico (PDA).
EOF

# Registrar en ollama
ollama create unibabot-pda -f Modelfile
```

Despues, cambiar `MODELO = "llama3.2"` a `MODELO = "unibabot-pda"` en `src/agent.py`.

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

## Fine-tuning

| Parametro | Valor |
|-----------|-------|
| Modelo base | Llama 3.2 3B Instruct |
| Tecnica | QLoRA (4-bit NF4 + LoRA r=16) |
| Dataset | 42 train + 5 validation (formato Alpaca) |
| Epochs | 3 |
| Learning rate | 2e-4 |
| Batch size efectivo | 8 (2 x 4 gradient accumulation) |
| Hardware | Google Colab T4 (16GB VRAM) |
| Resultado | Train loss 1.64 -> 1.26, Val loss 1.52 -> 1.15 |

## Autores

- Kevin Beltran Martinez (2220221003)
- Jeryleefth Lasso Motta (2220231074)

Ingenieria de Sistemas, Universidad de Ibague, 2026A
Asignatura: Agentes Inteligentes
