# UnibaBot PDA

Agente inteligente para la verificacion automatizada de Planes de Desarrollo Academico (PDA) de la Universidad de Ibague. El sistema recibe un PDA en formato PDF, lo evalua contra lineamientos institucionales codificados, y genera un reporte estructurado de cumplimiento.

## Contexto

Cada semestre, las oficinas de los programas academicos de la Universidad de Ibague deben verificar manualmente que mas de 20 PDAs cumplan con los lineamientos institucionales. Este proceso es lento, inconsistente y propenso a errores. UnibaBot PDA automatiza esta verificacion mediante un pipeline que combina extraccion de texto, busqueda semantica (RAG) y un modelo de lenguaje especializado via fine-tuning.

## Arquitectura

```
PDF del PDA
    |
    v
[1. Extraccion de texto]        src/pdf_parser.py
    |                            PyMuPDF -> bloques con metadata (fuente, bold)
    v
[2. Segmentacion por secciones]  Deteccion de encabezados via heuristicas +
    |                            lista de secciones conocidas (bilingue)
    v
[3. RAG: Retrieval]              src/rag/retriever.py
    |                            ChromaDB + embeddings (all-MiniLM-L6-v2)
    |                            179 reglas con filtro por curso
    v
[4. Prompt + LLM]                src/agent.py
    |                            Llama 3.2 3B via ollama
    |                            Fine-tuneado con QLoRA (42 ejemplos)
    v
[5. Reporte de cumplimiento]     results/reporte_cumplimiento.json
                                 JSON estructurado por seccion:
                                 cumple / no cumple / regla / correccion
```

## Estructura del proyecto

```
Unibabot_PDA/
  src/
    pdf_parser.py                # Extraccion y segmentacion de PDAs
    agent.py                     # Pipeline completo del agente
    generar_reglas.py            # Genera reglas desde JSON_archives/
    prompts/
      compliance_prompt.txt      # Template del prompt de evaluacion
    rag/
      ingest.py                  # Carga reglas en ChromaDB
      retriever.py               # Busqueda semantica de lineamientos
    fine_tuning/
      prepare_dataset.py         # Genera pares instruccion-respuesta
      generar_outputs.py         # Genera outputs con Llama 3.2
  data/
    lineamientos/
      reglas.json                # 179 reglas codificadas
    chroma_db/                   # Base vectorial persistida
    training_dataset.jsonl       # 42 ejemplos de entrenamiento
    validation_dataset.jsonl     # 5 ejemplos de validacion
  models/
    lora_adapter/                # Adaptador LoRA entrenado
  notebooks/
    fine_tuning.ipynb            # Notebook para Google Colab (QLoRA)
  results/
    reporte_cumplimiento.json    # Ultimo reporte generado
  PDAs/                          # PDAs reales en PDF (4 documentos)
  JSON_archives/                 # Datos institucionales (ABET, competencias)
  Docs/                          # Documentacion academica y presentaciones
  ROADMAP.md                     # Plan de implementacion por fases
  CLAUDE.md                      # Instrucciones del proyecto
  requirements.txt               # Dependencias Python
```

## Requisitos

- Python 3.12+
- ollama con Llama 3.2 3B
- Google Colab con GPU T4 (solo para fine-tuning)

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
ollama pull llama3.2

# Ingestar reglas en ChromaDB
python src/generar_reglas.py
python src/rag/ingest.py
```

## Uso

### Analizar un PDA

```bash
cd src
python agent.py "../PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14
```

El segundo argumento es el codigo del curso (opcional). Si se proporciona, el sistema filtra las reglas de competencias especificas de ese curso.

El reporte se guarda en `results/reporte_cumplimiento.json`.

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
