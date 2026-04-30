# UnibaBot PDA

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Test accuracy](https://img.shields.io/badge/test%20accuracy-1.000-success.svg)](#evaluacion)
[![LLM](https://img.shields.io/badge/LLM-Qwen%202.5%2014B-7c3aed.svg)](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2014-black.svg)](https://nextjs.org/)

Agente inteligente para la verificacion automatizada de Planes de Desarrollo Academico (PDA) de la Universidad de Ibague. El sistema recibe un PDA en formato PDF, lo evalua contra 179 lineamientos institucionales codificados, y genera un reporte estructurado de cumplimiento con evidencia citada y correcciones sugeridas.

> **Asignatura:** Agentes Inteligentes — Ingenieria de Software, Universidad de Ibague (2025-2026).
> **Autores:** Kevin Beltran Martinez (2220221003), Jeryleefth Lasso Motta (2220231074).
> **Reporte tecnico:** [Docs/UnibaBot_PDA.pdf](Docs/UnibaBot_PDA.pdf) (formato IEEE).

**Resultados sobre gold dataset (106 entradas, 6 PDAs reales) — produccion m17:**

| Split | Accuracy | Precision NC | Recall NC | Matched | Latencia |
|-------|----------|--------------|-----------|---------|----------|
| Train (51 entradas, 3 PDAs) | **1.000** | **1.000** | **1.000** | 51/51 | ~290s |
| Test hold-out (55 entradas, 3 PDAs nuevos) | **1.000** | **1.000** | **1.000** | 55/55 | ~330s |

*Docling + extraccion por evidencia + Qwen 2.5 14B. NC = clase NO CUMPLE (incumplimientos reales). Train: PDAs vistos durante el desarrollo. Test: PDAs nunca tocados. m17 anade enrichment LLM opt-in (correcciones prescriptivas + resumenes ejecutivo/didactico) sin afectar las metricas de cumplimiento.*

## Contexto

Cada semestre, las oficinas de los programas academicos de la Universidad de Ibague deben verificar manualmente que mas de 20 PDAs cumplan con los lineamientos institucionales. Este proceso es lento, inconsistente y propenso a errores. UnibaBot PDA automatiza esta verificacion mediante un pipeline hibrido que combina verificacion rule-based determinista, despacho explicito de reglas por seccion, y extraccion de declaraciones con **Qwen 2.5 14B** corriendo localmente en un MacBook Pro M3 18GB.

## Arquitectura

El sistema tiene **dos capas independientes**: el motor de cumplimiento (la inteligencia) y el stack de produccion (la operacion).

### Capa 1 — Motor de cumplimiento (pipeline AI)

```
PDF del PDA
    |
    v
[1. Extraccion + segmentacion]    src/pdf_parser.py
    |                             Docling + segmentacion por secciones
    v
[2. Rule-based estructural]       src/rules/estructural_checker.py
    |                             11 checkers deterministicos (EST-001..011)
    |                             100% precision en reglas estructurales
    v
[3. Clasificador de tipo PDA]     src/pda_classifier.py
    |                             Rechaza temprano docs que no son PDA
    |                             (papers, syllabi, escaneados sin OCR)
    v
[4. Despacho de reglas]           src/rag/rule_dispatcher.py
    |                             Mapea 168 reglas (reglas.json) a secciones
    |                             Match por nombre de seccion + keyword fallback
    v
[5. Extraccion de declaraciones]  src/rules/declaracion_extractor.py
    |                             1 llamada LLM por PDA (Qwen 2.5 14B)
    |                             Extrae codigos canonicos (C1, 1b, SP5, D4, ABET X.Y)
    |                             src/prompts/extraccion_prompt.txt
    v
[6. Matcher deterministico]       src/rules/declaracion_checker.py
    |                             Regex por tipo + set intersection
    |                             Compliance 100% reproducible y auditable
    v
[7. Enrichment LLM (opt-in)]      src/enrichment/correction_writer.py
    |                             src/enrichment/summary_writer.py
    |                             Cache SHA-256 idempotente
    v
[8. Reporte estructurado]         results/reports_<tag>.json
                                  regla_id / estado / evidencia / correccion
```

### Capa 2 — Stack de produccion (web + cola + worker)

```
Navegador (Next.js 14)                                      web/
    |        chat UI, dark mode, SSE de progreso
    |        upload con validacion sincrona y rechazo conversacional
    v
HTTP / SSE
    |
    v
FastAPI :8000     auth JWT, endpoints REST, SSE de progreso        src/api/
    |             validacion sincrona del PDA antes de encolar
    |             encola job en RQ
    v
Redis :6379       broker de RQ + canal pub/sub para progreso en vivo
    |
    v
RQ Worker         consume cola, corre el motor de cumplimiento     src/api/jobs/
                  publica eventos de progreso por canal pub/sub    SimpleWorker en macOS y Windows
                  guarda reporte en data/reports/                  Worker estandar (fork) en Linux
```

Cada PDA subido por la web pasa por el motor de cumplimiento exactamente igual que cuando se invoca por CLI: el stack de produccion solo cambia COMO se invoca y COMO se entregan los resultados, no QUE evalua. Eso preserva la auditabilidad: el reporte que ve la oficina del programa academico es identico al reporte que produce `python src/agent.py` localmente.

**Evolucion de resultados — hitos principales:**

| Hito | Descripcion | Accuracy | Prec NC | Recall NC | Matched | Latencia |
|------|-------------|----------|---------|-----------|---------|----------|
| baseline | Llama 3.2 3B sin mejoras (gold 48) | 0.351 | 0.000 | 0.000 | 37/48 | 565s |
| m8b | Pipeline RAG+LLM completo (Llama 3.1 8B, gold 48) | 1.000* | 1.000 | 1.000 | 45/48 | 236s |
| m11 | Rule-driven: 100% cobertura (gold 57+55) | 0.895 / 0.873 | 0.625 / 0.818 | 0.625 / 0.857 | 57/57 + 55/55 | 213s / 249s |
| m12 | Qwen 2.5 14B como modelo LLM (gold 57+55) | 0.930 / 0.891 | 1.000 / 0.826 | 0.500 / 0.905 | 57/57 + 55/55 | 441s / 366s |
| m13 | Extractor+matcher deterministico | 0.965 / 0.982 | 1.000 / 0.900 | 0.500 / 1.000 | 57/57 + 55/55 | ~95s / ~120s |
| m14 | Docling reemplaza PyMuPDF | 0.965 / 1.000 | 1.000 / 1.000 | 0.500 / 1.000 | 57/57 + 55/55 | ~85s / ~80s |
| **m15 Train** | **Extraccion por evidencia (gold consolidado 51+55)** | **1.000** | **1.000** | **1.000** | **51/51** | **~290s** |
| **m15 Test** | **Hold-out 3 PDAs nuevos** | **1.000** | **1.000** | **1.000** | **55/55** | **~330s** |
| m16 | Infraestructura produccion: common/, logging, excepciones | **1.000** | **1.000** | **1.000** | 51/51 + 55/55 | ~290s / ~330s |
| **m17** | **Enrichment LLM opt-in (correcciones prescriptivas + resumenes), cache idempotente** | **1.000** | **1.000** | **1.000** | 51/51 + 55/55 | ~290s / ~330s* |

*m17 no toca el motor de cumplimiento: las metricas se mantienen identicas por construccion (`evaluate.py` lee solo `regla_id` y `estado`). El enrichment anade `correccion_enriquecida` y `resumenes` al reporte cuando se activan los flags `--enriquecer` y `--resumen`. Latencia adicional con cache frio: +30-45s; con cache caliente: 0ms (idempotencia bit-a-bit).

*m8b: accuracy 1.000 sobre 45/48 entradas matcheadas, 3 excluidas por retrieval semantico. El salto de m8b a m11 no es una regresion: m11 introdujo evaluacion 100% deterministica revelando incumplimientos que el retrieval semantico omitia por no recuperarlos en el top-k.*

Ver [results/accuracy_progression.md](results/accuracy_progression.md) y [results/rag_vs_rules_benchmark.md](results/rag_vs_rules_benchmark.md) para el detalle por iteracion y la comparacion empirica entre las dos arquitecturas exploradas.

## Estructura del proyecto

```
Unibabot_PDA/
  src/                                # Motor de cumplimiento (capa 1)
    agent.py                          # Pipeline completo invocado desde CLI / API / Streamlit
    pdf_parser.py                     # Extraccion + segmentacion con Docling
    pda_classifier.py                 # Clasificador rule-based "esto es un PDA?"
    evaluate.py                       # Evaluacion contra gold dataset (train/test)
    generar_reglas.py                 # Genera reglas desde JSON_archives/
    schemas.py                        # Modelos Pydantic para validacion estricta
    common/
      text.py                         # Normalizacion de texto (normalizar())
      logging_config.py               # structlog + decorador @timed
      exceptions.py                   # Excepciones tipadas (UnibabotError, LLMError, InvalidPDAError)
      ollama_client.py                # Wrapper ollama con timeout configurable
    prompts/
      extraccion_prompt.txt           # Prompt de extraccion de codigos declarados (m13)
      compliance_prompt.txt           # Prompt de evaluacion LLM (fallback legacy)
      retry_prompt.txt                # Prompt de retry para JSON invalido
      correccion_prescriptiva.txt     # Prompt para correccion enriquecida (m17)
      resumenes.txt                   # Prompt para resumenes oficina + docente (m17)
    rules/
      estructural_checker.py          # 11 checkers rule-based (EST-001..011)
      declaracion_extractor.py        # Extractor LLM de codigos canonicos (m13)
      declaracion_checker.py          # Matcher deterministico (m13)
    enrichment/                       # Enrichment LLM opt-in (m17)
      cache.py                        # Cache en disco SHA-256 (idempotencia bit-a-bit)
      correction_writer.py            # Texto prescriptivo por hallazgo NO CUMPLE
      summary_writer.py               # Resumenes ejecutivo (oficina) + didactico (docente)
    rag/
      rule_dispatcher.py              # PRODUCCION: despacho determinista por seccion (m11+)
      seccion_mapping.py              # PRODUCCION: keyword_parser -> [seccion_pda]
      ingest.py / retriever.py /
      embeddings.py / reranker.py     # ALTERNATIVO: via RAG semantica (m0-m10), referencia comparativa
    api/                              # Backend FastAPI (m18)
      main.py                         # App factory + middlewares (CORS, JWT)
      auth.py                         # Login, registro, JWT
      config.py                       # Settings via pydantic-settings
      db.py                           # SQLAlchemy + SQLite, sesiones por request
      models.py / schemas.py          # ORM + DTOs
      routes/auth.py                  # /api/auth/{login,register,me}
      routes/analyses.py              # POST upload + validacion sincrona, GET list/detail, SSE de progreso
      jobs/queue.py                   # Encolar al RQ
      jobs/tasks.py                   # Task que invoca agent.analizar_pda con callback de progreso
      jobs/progress.py                # SSE generator que lee del canal pub/sub Redis
      jobs/worker.py                  # Entrypoint del worker (SimpleWorker en macOS/Windows)
  web/                                # Frontend Next.js 14 (m18)
    src/app/                          # App Router: /login, /register, /dashboard
    src/components/                   # chat-composer, chat-message, chat-rejection, ui/* (shadcn-style)
    src/hooks/                        # use-auth, use-analyses, use-progress-stream, use-toast
    src/lib/                          # api-client (fetch + JWT), types, utils
    tests/                            # Playwright E2E
    Dockerfile                        # Build production con node:20-alpine
    scripts/icloud-fix.js             # Postinstall portable (Node, sin bash)
  tests/                              # Suite Python
    test_pda_classifier.py            # 7 casos sinteticos del clasificador
    api/test_auth.py / test_analyses.py # 10 tests del backend (incluye casos 422 de rejection)
    api/conftest.py                   # Fixtures (DB en memoria, mocks, SYNC_MODE)
  data/
    lineamientos/reglas.json          # 179 reglas codificadas (11 EST + 168 COMP)
    gold_labels.json                  # Gold train (51 entradas, 3 PDAs)
    gold_labels_test.json             # Gold test hold-out (55 entradas, 3 PDAs)
    unibabot.db                       # SQLite del backend (gitignored)
  results/
    accuracy_progression.md           # Tabla de progresion de accuracy (m1-m17)
    rag_vs_rules_benchmark.md         # Head-to-head rule-driven vs RAG semantico
    metrics_<tag>.json                # Metricas por snapshot (gitignored)
    reports_<tag>.json                # Reportes crudos del agente (gitignored)
  cache/enrichment/                   # Cache LLM hasheado SHA-256 (gitignored, m17)
  PDAs/                               # PDAs reales en PDF (gitignored, datos institucionales)
  JSON_archives/                      # Datos institucionales (ABET, competencias, cursos)
  Docs/UnibaBot_PDA.pdf               # Reporte tecnico IEEE (drafts y .tex gitignored)
  docker-compose.yml                  # Orquesta redis + api + worker + web
  api.Dockerfile / worker.Dockerfile  # Imagenes Python 3.12 con FastAPI / RQ
  streamlit_app.py + webapp/          # Demo legacy con Streamlit (sigue funcional)
  requirements.txt                    # Dependencias core (pipeline + Streamlit)
  requirements-api.txt                # Adicionales para FastAPI + RQ
  LICENSE                             # MIT
```

## Requisitos

- Python 3.12+
- **ollama** con Qwen 2.5 14B (default) y/o Llama 3.1 8B (comparativo)
- MacBook Pro M3 18GB o equivalente (Qwen 2.5 14B requiere ~9GB de VRAM)

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

# Generar reglas a partir de los datos institucionales
python src/generar_reglas.py
```

## Uso

### Interfaz web "produccion" (FastAPI + Next.js, m18)

Stack orientado a entrega final y operacion multi-usuario. Streamlit sigue funcionando como demo de avance; este stack es la ruta canonica para deployment.

**Caracteristicas principales:**

- **Auth por usuario** con JWT (registro, login, validacion en cada request).
- **Cola asincrona de jobs** (RQ + Redis): el upload responde en ~5-10s con un `analysis_id`; el analisis pesado (~5 min) corre en el worker sin bloquear la API.
- **SSE de progreso en vivo**: el frontend se suscribe a `/api/analyses/{id}/events` y recibe eventos por canal pub/sub Redis (`extractor_start`, `extractor_done`, `enrichment_start`, etc.). El usuario ve el progreso seccion por seccion sin polling.
- **Validacion sincrona del PDA antes de encolar**: si el documento no parece un PDA (paper, syllabus, escaneado sin OCR, corrupto), el endpoint responde HTTP 422 con un codigo y mensaje natural. El frontend renderiza la respuesta como un mensaje del asistente en el chat ("Este documento parece academico pero no es un PDA. Solo reconoci 3/11 secciones canonicas..."), no como toast efimero.
- **UI estilo conversacion**: dashboard en Next.js 14 con dark mode, mensajes de usuario y asistente, descarga del reporte JSON, listado de analisis pasados.
- **Cobertura por tests:** suite pytest del backend (10/10 verde) + tests Playwright E2E del frontend.

**Recomendado en cualquier sistema operativo:** levantar todo con Docker Compose. Un solo comando, cero dependencias en el host (excepto Docker y Ollama):

```bash
# Asegurate de que ollama esta corriendo en el host (ollama serve)
docker compose up --build
```

Esto arranca redis + api + worker + web. Frontend en `http://localhost:3000`, API en `http://localhost:8000`. El `worker` corre en un contenedor Linux (fork natural), asi que **es la unica via soportada en Windows** dado que RQ no soporta `os.fork()` nativo.

**Dev local en macOS / Linux** (mas rapido para iterar, requiere 4 terminales):

```bash
# 1. Backend
pip install -r requirements-api.txt
cp .env.example .env  # configurar JWT_SECRET con: openssl rand -hex 32
docker run --rm -d --name unibabot-redis -p 6379:6379 redis:7-alpine
make dev-api      # uvicorn FastAPI en :8000
make dev-worker   # worker RQ en otra terminal

# 2. Frontend
cd web
cp .env.local.example .env.local
npm install
npm run dev       # Next.js en http://localhost:3000
```

En macOS el worker se autoselecciona como `SimpleWorker` (sin fork) para evitar crashes de Docling/torch con objc fork-safety. En Linux usa el `Worker` estandar con fork. En Windows nativo solo `SimpleWorker` funciona, pero la ruta soportada es Docker Compose.

**Notas sobre `npm install`:** el postinstall hook (`web/scripts/icloud-fix.js`) corre en Node y es noop en cualquier sistema que no este bajo iCloud Drive de macOS. No requiere bash, asi que funciona en Windows nativo, Linux nativo, e imagenes Docker Alpine sin modificacion.

### Interfaz web (Streamlit, demo de avance)

```bash
streamlit run streamlit_app.py
```

Abre la UI en `http://localhost:8501`. El flujo es:

1. Subir un PDA en PDF, opcionalmente escribir el codigo del curso (ej: `22A14`) y elegir modelo.
2. **Enriquecimientos LLM (opcionales, m17):** dos toggles antes de analizar: "Correcciones enriquecidas" anade texto prescriptivo con codigo literal entre comillas a cada hallazgo NO CUMPLE; "Resumenes ejecutivo y didactico" anade dos resumenes al inicio del reporte (uno para la oficina del programa, otro para el docente). Ambos cacheados: la segunda corrida del mismo PDA es instantanea.
3. Al pulsar "Analizar PDA" se ve el progreso en vivo seccion por seccion.
4. El reporte se muestra con metricas globales, tabs (Estructural / Por seccion / Resumen) y acordeones con badges coloreados por hallazgo. Si los toggles de enrichment estaban activos, los resumenes aparecen como card al inicio y la correccion enriquecida queda como principal en cada NO CUMPLE (la templada se conserva como expander de referencia).
5. Cada reporte se guarda automaticamente en `results/history/` y aparece en el sidebar para consultar despues sin re-analizar.

### Analizar un PDA (CLI)

```bash
# Default: usa Qwen 2.5 14B (m17 produccion, accuracy 1.000 en test hold-out)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14

# Con modelo explicito
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 qwen    # Qwen 2.5 14B (default)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 8b      # Llama 3.1 8B (legacy)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 baseline # Llama 3.2 3B (baseline)

# Enrichment LLM opt-in (m17)
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 --enriquecer    # correccion prescriptiva por NO CUMPLE
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 --resumen       # resumenes oficina + docente
python src/agent.py "PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf" 22A14 qwen --enriquecer --resumen  # ambos
```

El segundo argumento es el codigo del curso (opcional). Si se proporciona, el sistema filtra las reglas de competencias especificas de ese curso. El reporte se guarda en `results/reporte_<modelo>.json`. Los flags `--enriquecer` y `--resumen` (m17) anaden los campos `correccion_enriquecida` y `resumenes` al reporte; ambos cacheados en `cache/enrichment/` para idempotencia bit-a-bit.

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

## Dos caminos: rule-driven vs RAG semantico

El proyecto exploro dos arquitecturas antes de quedarse con la actual. Ambos siguen en el repo como evidencia comparativa:

- **Rule-driven (PRODUCCION, m11+):** `rag/rule_dispatcher.py` + `rag/seccion_mapping.py`. Despacha cada regla a la seccion del PDA donde debe declararse via match por nombre + keyword fallback. Sin embeddings, sin base vectorial, sin dependencias ML pesadas. **Mas escalable**: 168 reglas hoy, miles manana, mismo costo en tiempo de inferencia (O(n) lookup en memoria).
- **RAG semantico (ALTERNATIVO, m0-m10):** `rag/ingest.py` + `rag/retriever.py` + `rag/embeddings.py` + `rag/reranker.py`. ChromaDB + SBERT multilingue + cross-encoder reranker recuperaban reglas top-k por similitud. Funcional pero mas costoso (ingesta inicial, persistencia de la base vectorial, dependencias) y con problemas de cobertura: m11 demostro que pasar a despacho explicito subio la cobertura del gold de 38/55 a 55/55.

Tambien se exploro **fine-tuning con QLoRA (m7)**: Llama 3.2 3B fine-tuneado con 42 ejemplos en Colab T4. El modelo entro en loops de generacion y fue descartado. La mejora vino despues por ingenieria del pipeline (m8-m13), no por especializacion del modelo. Los scripts y datasets de fine-tuning fueron eliminados del repo; el registro completo del experimento queda en el reporte IEEE.

Ver [Docs/UnibaBot_PDA.pdf](Docs/UnibaBot_PDA.pdf) y [results/accuracy_progression.md](results/accuracy_progression.md) para el detalle de cada iteracion.

## Decisiones tecnicas clave

1. **LLM para extraccion, no para razonamiento:** El LLM es fuerte extrayendo codigos ("C1", "SP5") de texto, pero debil razonando si una declaracion informal cumple una regla formal. m13 separa los dos roles: LLM extrae, codigo Python decide.

2. **Rule-driven vs retrieval-driven:** m11 invirtio el flujo. En vez de "busca semanticamente las reglas mas similares al texto", el sistema ahora "para cada regla aplicable al curso, encuentra la seccion del PDA donde debe declararse". Esto garantiza cobertura 100%.

3. **Determinismo en compliance:** El veredicto final de cumplimiento es 100% reproducible (regex + set intersection). Solo la fase de extraccion tiene estocasticidad.

4. **Despacho explicito sin retrieval semantico:** `rule_dispatcher.py` mapea cada regla al nombre de seccion del PDA donde debe declararse, con keyword-fallback cuando el nombre no matchea. No hay base vectorial ni embeddings en produccion: el matching es por strings normalizados, 100% reproducible, sin dependencias ML pesadas, y escalable a miles de reglas sin re-indexacion. La via RAG semantica (`ingest.py`/`retriever.py`/`embeddings.py`/`reranker.py`) sigue en `src/rag/` como referencia comparativa.

5. **Gold dataset como evidencia de generalizacion:** El test hold-out con 3 PDAs nunca vistos durante el desarrollo (accuracy 1.000) demuestra que el sistema no memoriza patrones de los PDAs de entrenamiento.

## Escalabilidad y operacion

El stack de produccion (capa 2) esta disenado para escalar desde un solo usuario en un Mac M3 hasta una oficina academica con varios programas usando el sistema simultaneamente.

**Cola asincrona desacopla upload de inferencia.** El endpoint `POST /api/analyses` valida el documento (~5-10s con Docling) y encola un job en RQ; el HTTP responde 202 con un `analysis_id` antes de ejecutar la fase pesada. El worker consume la cola al ritmo del LLM (~5 min por PDA). Si llegan 20 PDAs en 5 minutos, no se pierde ninguno: la cola los serializa y el frontend muestra estado `pending` hasta que termina cada uno.

**API stateless, escala horizontal.** FastAPI no guarda estado por request (el JWT lleva el `user_id`, la sesion vive solo en SQLite). Detras de un load balancer se puede correr N replicas de la API sin coordinacion. SQLite se cambia por Postgres con un solo cambio de variable de entorno (`DATABASE_URL`).

**Worker stateless, escala N replicas.** Cada worker pulla del mismo Redis. Anadir un segundo worker dobla el throughput hasta saturar Ollama (que es el cuello de botella real, no la app). Si Ollama se mueve a un servidor con GPU dedicada (`OLLAMA_HOST=http://gpu-server:11434`), los workers en Linux/Docker pueden correr en CPU normal sin afectar la latencia.

**Cache SHA-256 idempotente.** El enrichment LLM (m17) cachea cada salida hasheada por modelo + prompt + inputs. Re-correr el mismo PDA con `--enriquecer --resumen` la segunda vez no invoca al LLM: lectura directa de `cache/enrichment/<sha>.json`. La cache se monta como volumen Docker, asi que sobrevive reinicios de containers.

**Validacion temprana evita procesar basura.** El clasificador rule-based (`pda_classifier.py`) corre sincrono en el upload y rechaza documentos que no son PDAs (papers, syllabi, escaneados sin OCR) ANTES de encolar. El usuario no espera 5 minutos para ver "no es un PDA"; recibe el rechazo en segundos como respuesta del asistente en el chat. Esto protege la cola de jobs imposibles y reduce costo de Ollama para uploads erroneos.

**Observabilidad operacional.**

- `structlog` con output JSON activable por env (`UNIBABOT_LOG_JSON=1`). Listo para Splunk / Datadog / Grafana Loki.
- Decorador `@timed("event")` en operaciones criticas (parsing, extraccion LLM, validacion).
- SSE per-analysis stream: cada job publica eventos en el canal `progress:{analysis_id}` y la API los reenvia al frontend. Util para diagnostico ("se quedo pegado en `extractor_start`").
- Excepciones tipadas (`UnibabotError` -> `LLMError` -> `LLMUnavailableError` / `LLMTimeoutError` / `LLMResponseError`, `PDFParseError`, `InvalidPDAError`). Distingue fatales de recuperables.

**Cross-platform comprobado.**

- macOS: dev local con 4 terminales o docker-compose. `SimpleWorker` evita crashes de fork-safety con Cocoa-bound libs.
- Linux: dev local con `Worker` estandar (fork natural) o docker-compose. Recomendado para deploy real.
- Windows: docker-compose es la unica via soportada (RQ no soporta `os.fork()` nativo en Windows; el worker corre en contenedor Linux).
- iCloud Drive en macOS: el postinstall de `web/` es un script Node que detecta iCloud y crea symlinks a `.nosync/` para evitar evictions. En cualquier otro sistema hace noop.

**Surface de dependencias minima.** El motor de cumplimiento usa Docling, Qwen via Ollama, y librerias estandar de Python. El stack de produccion suma FastAPI, RQ, Redis, Next.js. La via RAG semantica (ChromaDB + SBERT + cross-encoder) sigue como ruta alternativa pero NO esta en la dependencia critica del path de produccion: removerla del entorno no rompe nada esencial.

## Limitaciones identificadas

1. **Latencia de extraccion:** ~290-330s por PDA. La fase de extraccion enriquecida por evidencia con Qwen 2.5 14B domina el tiempo total de inferencia.
2. **Parser dependiente del formato PDF:** PDAs con tablas complejas o escaneados como imagen pueden no segmentarse correctamente. Docling mejora notablemente sobre PyMuPDF pero no es infalible.
3. **Dataset de 6 PDAs:** Mas PDAs (20+) permitirian metricas estadisticamente mas robustas para la clase NC.
4. **Declaraciones informales sin codigo canonico:** El extractor puede no detectar competencias descritas con lenguaje muy informal cuando no hay ni codigo literal ni nombre canonico reconocible en el texto.

## Autores

- Kevin Beltran Martinez (2220221003)
- Jeryleefth Lasso Motta (2220231074)

Ingenieria de Sistemas, Universidad de Ibague, 2026A
Asignatura: Agentes Inteligentes

## Licencia y datos institucionales

El codigo de este repositorio se distribuye bajo licencia [MIT](LICENSE). Esto cubre todo el pipeline (`src/`), el frontend (`web/`), tests, y la definicion de los lineamientos institucionales en `data/lineamientos/`.

Los PDFs de PDAs reales bajo `PDAs/` y `data/chroma_db/` son datos academicos de la Universidad de Ibague y NO forman parte del repositorio publico (ver `.gitignore`). Reproducir las metricas requiere acceso autorizado a los PDAs originales del programa academico evaluado.
