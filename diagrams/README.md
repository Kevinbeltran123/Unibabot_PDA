# UnibaBot PDA — Diagramas de Arquitectura

Diagramas de arquitectura, flujo y evolucion del sistema UnibaBot PDA.
Preparados para presentacion en conferencia de ingenieria de software.

## Orden recomendado para la presentacion

| # | Archivo | Titulo | Que muestra |
|---|---------|--------|-------------|
| 1 | [01_architecture.mmd](01_architecture.mmd) | Arquitectura del Sistema | Vision global: dos capas, cuatro procesos, flujo completo |
| 2 | [02_pipeline.mmd](02_pipeline.mmd) | Pipeline de Cumplimiento | Los 6 pasos desde PDF hasta reporte con 179 hallazgos |
| 3 | [03_llm_philosophy.mmd](03_llm_philosophy.mmd) | LLM Extrae, Python Decide | Secuencia exacta de la UNA llamada LLM vs todos los pasos Python |
| 4 | [04_web_stack.mmd](04_web_stack.mmd) | Stack Web y Despliegue | Los 4 procesos con puertos, Redis, SSE y rutas FastAPI |
| 5 | [05_rule_taxonomy.mmd](05_rule_taxonomy.mmd) | Taxonomia de 179 Lineamientos | Clasificacion completa: EST, COMP, SABER PRO, ABET |
| 6 | [06_rag_vs_rules.mmd](06_rag_vs_rules.mmd) | RAG vs Rule-driven | Comparacion de enfoques: por que se descarno RAG |
| 7 | [07_accuracy_journey.py](07_accuracy_journey.py) | Evolucion de Accuracy | Grafico con datos reales de 15 milestones (0.351 -> 1.000) |

## Como renderizar

### Opcion A — Linea de comandos (recomendada para alta resolucion)

Requiere Node.js instalado.

```bash
# Instalar Mermaid CLI una sola vez
npm install -g @mermaid-js/mermaid-cli

# Generar todos los diagramas en SVG/PNG + grafico Python
bash diagrams/render.sh
# Output: diagrams/rendered/
```

### Opcion B — VS Code (previsualizar en editor)

Instalar la extension **Markdown Preview Mermaid Support** (`bierner.markdown-mermaid`) o **Mermaid Preview** (`vstirbu.vscode-mermaid-preview`). Abrir cualquier `.mmd` y usar `Cmd+Shift+V`.

### Opcion C — GitHub (sin instalacion)

Los archivos `.mmd` se renderizan automaticamente en GitHub si se incrustan en un bloque de codigo markdown con el identificador `mermaid`. El repositorio incluye los archivos fuente, no las imagenes generadas.

### Opcion D — mermaid.live (online)

Copiar el contenido de cualquier `.mmd` en [mermaid.live](https://mermaid.live) para previsualizar y exportar.

## Grafico de accuracy (Diagrama 7)

El archivo `07_accuracy_journey.py` genera `rendered/accuracy_journey.png` y `.svg`.

```bash
# Con el venv del proyecto
~/.venvs/unibabot/bin/pip install matplotlib
~/.venvs/unibabot/bin/python diagrams/07_accuracy_journey.py
```

Los datos son los mismos que aparecen en `results/accuracy_progression.md`.

## Descripcion detallada por diagrama

### 01 — Arquitectura del Sistema

Muestra las dos capas del sistema y como se conectan:

- **Layer 2 (Stack de Produccion):** Next.js 14, FastAPI, Redis, RQ Worker, SQLite
- **Layer 1 (Motor de Cumplimiento):** los 6 modulos Python del pipeline
- **IA Local:** Ollama con Qwen 2.5 14B (sin acceso a internet)
- **Cache:** SHA-256 para idempotencia del enriquecimiento

### 02 — Pipeline de Cumplimiento

El flujo completo de datos desde el PDF de entrada hasta el reporte final:

1. `pda_classifier.py` — validacion previa al encolado
2. `pdf_parser.py` — Docling, extraccion layout-aware con TableFormer
3. `estructural_checker.py` — 11 checks deterministicos (EST-001..011)
4. `rule_dispatcher.py` — mapeo de 168 reglas COMP a secciones del PDA
5. `declaracion_extractor.py` — UNA llamada a Qwen 2.5 14B con validacion de evidencia
6. `declaracion_checker.py` — matcher deterministico: regex + set intersection
7. Consolidacion del reporte JSON con 179 hallazgos

### 03 — LLM Extrae, Python Decide

Diagrama de secuencia que muestra exactamente que hace cada componente:

- Python maneja los 11 checks estructurales sin LLM
- El LLM recibe el contexto y propone codigos canonicos con snippets
- Python valida la evidencia (bloquea alucinaciones)
- Python ejecuta el matching deterministico y emite el veredicto

Principio clave: el veredicto de cumplimiento es 100% reprodicuble y auditable.

### 04 — Stack Web y Despliegue

Los cuatro procesos que corren en paralelo:

| Proceso | Tecnologia | Puerto |
|---------|-----------|--------|
| Frontend | Next.js 14 + React | 3000 |
| Backend | FastAPI + uvicorn | 8000 |
| Queue | Redis | 6379 |
| Worker | RQ (SimpleWorker/Worker) | — |

Muestra el flujo SSE para progreso en tiempo real y las rutas de la API.

### 05 — Taxonomia de 179 Lineamientos

Arbol completo de las reglas evaluadas:

- 11 estructurales (EST-001..011): secciones, tabla de evaluacion, fechas, bibliografia
- 168 de competencias por tipo: especificas, genericas, SABER PRO, dimensiones, ABET

### 06 — RAG vs Rule-driven

La decision arquitectonica mas importante del proyecto:

- **RAG descartado:** ChromaDB + embeddings cubria solo el 69% de las reglas en test (38/55)
- **Rule-driven adoptado:** iteracion deterministica sobre metadatos, cobertura 100% (55/55)
- **Fallback semantico preservado:** cross-encoder multilingue solo cuando el nombre de seccion no coincide

### 07 — Evolucion de Accuracy (datos reales)

Datos de `results/accuracy_progression.md`:

- Fase 1 (48 entradas): de 0.351 (baseline) a 1.000 con checks Python + Llama 3.1 8B
- Fase 2 (55 entradas hold-out): de 0.974 (RAG) a 1.000 con Docling + evidence validator
- La caida de 1.000 a 0.873 en m11 es el salto de cobertura 38->55, no una regresion

## Tecnologias representadas

- Python 3.12, FastAPI, SQLAlchemy, RQ, Redis
- Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- Docling (IBM), Qwen 2.5 14B via Ollama
- SQLite, SHA-256 cache

## Autores

Kevin Beltran Martinez (2220221003) y Jeryleefth Lasso Motta (2220231074)
Universidad de Ibague — Agentes Inteligentes, Ingenieria de Software, 2025-2026
