# UnibaBot PDA -- Roadmap de Implementacion

**Proyecto:** Agente inteligente para verificacion de cumplimiento de PDAs
**Equipo:** Kevin Beltran, Jeryleefth Lasso
**Plazo:** ~3 semanas (28 marzo - 18 abril 2026)
**Hardware:** MacBook Pro M3 18GB (Llama 3.2 3B local via ollama) + Google Colab T4 (fine-tuning)

> **Nota historica:** Este documento es el roadmap original (Fases 0-6) tal como se planeo a finales de marzo de 2026. Describe la arquitectura RAG + fine-tuning que se exploro en las primeras iteraciones (m0-m7). El pipeline de produccion actual es distinto: rule-driven + extraccion deterministica con Qwen 2.5 14B. Ver [README.md](README.md) para la arquitectura vigente, y la seccion **Iteraciones post-roadmap (m7-m17)** al final de este archivo para la evolucion completa.

---

## Vision general del pipeline

```
PDF del PDA
    |
    v
[1. Extraccion de texto] -- PyMuPDF / pdfplumber
    |
    v
[2. Segmentacion por secciones] -- detectar encabezados del PDA
    |
    v
[3. RAG: Retrieval] -- buscar lineamientos relevantes en ChromaDB
    |                   usando sentence-transformers multilingue
    v
[4. Prompt + LLM] -- Llama 3.2 3B fine-tuneado con QLoRA
    |                  recibe: seccion del PDA + lineamientos + instruccion
    v
[5. Reporte de cumplimiento] -- JSON/texto estructurado por seccion
                                 cumple / no cumple / regla violada / correccion
```

---

## Fase 0: Datos y entorno (Dias 1-3)

**Meta:** Tener toda la materia prima lista y el entorno funcionando.

### Tareas

- [x] **0.1** Obtener 3-5 PDAs reales en PDF de la profesora (4 PDAs en `PDAs/`)
- [x] **0.2** Obtener los lineamientos institucionales (derivados de JSON_archives/: ABET, competencias, cursos)
- [x] **0.3** Codificar los lineamientos en formato estructurado (179 reglas en `data/lineamientos/reglas.json`, generadas por `src/generar_reglas.py`)
- [x] **0.4** Instalar ollama y descargar Llama 3.2 3B (`ollama pull llama3.2`)
- [x] **0.5** Crear entorno virtual Python y archivo `requirements.txt`
- [x] **0.6** Verificar que el modelo responde correctamente en espanol via ollama

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| PDAs de prueba | `data/pdas/*.pdf` |
| Lineamientos codificados | `data/lineamientos/reglas.json` |
| Dependencias | `requirements.txt` |

### Por que esta fase importa

Sin lineamientos claros no hay agente posible. Los lineamientos son el equivalente a las "reglas del juego": el agente solo puede verificar cumplimiento si conoce las reglas contra las cuales comparar. Igualmente, probar que el modelo corre local el dia 1 evita sorpresas mas adelante.

### Dependencias de librerias (inicial)

```
# requirements.txt (se ira ampliando)
pymupdf>=1.24.0          # extraccion de PDF
pdfplumber>=0.11.0        # alternativa de extraccion
chromadb>=0.5.0           # base de datos vectorial
sentence-transformers>=3.0.0  # embeddings multilingues
langchain>=0.2.0          # orquestacion del pipeline RAG
ollama>=0.3.0             # cliente Python para ollama
```

---

## Fase 1: Extraccion de texto del PDF (Dias 3-5)

**Meta:** Dado un PDA en PDF, extraer el texto limpio y segmentado por secciones.

### Tareas

- [x] **1.1** Implementar extraccion basica de texto con PyMuPDF (texto pagina por pagina)
- [x] **1.2** Identificar los encabezados tipicos de un PDA (resultados de aprendizaje, metodologia, cronograma, acciones de mejora, etc.) a partir de los PDAs reales
- [x] **1.3** Implementar segmentacion: dado el texto extraido, dividirlo en un diccionario `{nombre_seccion: contenido}`
- [x] **1.4** Validar manualmente con 2-3 PDAs: comparar extraccion vs. PDF original y corregir errores (validado con 4 PDAs, refinado con lista de secciones conocidas)

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| Parser de PDF | `src/pdf_parser.py` |
| Tests de extraccion | `tests/test_pdf_parser.py` |

### Concepto clave: por que segmentar

El agente evalua seccion por seccion, no el documento completo. Esto es lo que permite generar reportes como "la seccion Resultados de Aprendizaje NO cumple la regla X" en vez de solo "el PDA no cumple". La granularidad de la segmentacion determina la granularidad del reporte.

---

## Fase 2: RAG -- Base de conocimiento vectorial (Dias 5-8)

**Meta:** Construir el sistema que, dado un fragmento del PDA, recupera los lineamientos relevantes.

### Tareas

- [x] **2.1** Hacer chunking de los lineamientos: cada regla = 1 chunk (179 reglas ya estaban segmentadas desde `reglas.json`)
- [x] **2.2** Generar embeddings con modelo default de ChromaDB (all-MiniLM-L6-v2 via ONNX)
- [x] **2.3** Almacenar en ChromaDB con metadata asociada (tipo, seccion_pda, aplica_a)
- [x] **2.4** Implementar funcion de retrieval: `recuperar_lineamientos(texto, top_k=5, codigo_curso)` con filtro por curso
- [x] **2.5** Probar retrieval manualmente: verificado con queries de "resultados de aprendizaje" y "competencias" con filtro 22A14
- [x] **2.6** Ajustar: top_k=5 por defecto, se ajustara en Fase 3 si el LLM necesita mas contexto

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| Ingesta de lineamientos | `src/rag/ingest.py` |
| Base vectorial | `src/rag/vector_store.py` |
| Retriever | `src/rag/retriever.py` |

### Conceptos clave

**Embeddings:** Un embedding convierte texto en un vector de numeros (ej: 384 dimensiones) que representa su significado semantico. Textos con significado similar tienen vectores cercanos en el espacio. Esto permite buscar por "significado" en vez de por palabras exactas.

**Chunking:** Si metes un documento de 10 paginas como un solo vector, pierde especificidad. Si cada regla es un vector independiente, la busqueda es precisa: "dame las reglas sobre resultados de aprendizaje" solo trae reglas de esa categoria.

**Por que ChromaDB:** Es la base vectorial mas simple de usar (se instala con pip, corre local sin servidor, persiste en disco). Para un dataset de ~100 reglas es mas que suficiente. Alternativas como FAISS o Pinecone son para escalas mucho mayores.

---

## Fase 3: Pipeline RAG + LLM sin fine-tuning (Dias 8-11)

**Meta:** Conectar todo en un pipeline end-to-end y establecer un baseline de rendimiento.

### Tareas

- [x] **3.1** Disenar el prompt de evaluacion (`src/prompts/compliance_prompt.txt`)
- [x] **3.2** Conectar ollama (Llama 3.2 3B) al pipeline via API de Python
- [x] **3.3** Implementar el agente completo: `src/agent.py` (PDF -> secciones -> RAG -> LLM -> reporte JSON)
- [x] **3.4** Definir el formato de salida del reporte (JSON: seccion, hallazgos, estado, evidencia, correccion)
- [x] **3.5** Pasar PDA de Intelligent Agents (22A14) por el pipeline -- reporte generado en `results/reporte_cumplimiento.json`
- [x] **3.6** Documentar el baseline: resultados en `results/reporte_cumplimiento.json`, evidencias parciales, sin fine-tuning

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| Agente (pipeline completo) | `src/agent.py` |
| Template de prompt | `src/prompts/compliance_prompt.txt` |
| Resultados baseline | `results/baseline_evaluation.md` |

### Concepto clave: por que medir un baseline

El baseline responde la pregunta: "que tan bueno es el modelo SIN fine-tuning?" Si el baseline ya es 70% correcto, el fine-tuning apunta a llevarlo a 85-90%. Si el baseline es 30%, hay que investigar si el problema es el retrieval, el prompt, o el modelo. Sin baseline, no puedes medir el impacto del fine-tuning.

### Estructura del prompt (borrador)

```
Eres un evaluador academico de la Universidad de Ibague. Tu tarea es verificar
si la siguiente seccion de un Plan de Desarrollo Academico (PDA) cumple con
los lineamientos institucionales.

SECCION DEL PDA:
{seccion_pda}

LINEAMIENTOS INSTITUCIONALES RELEVANTES:
{lineamientos_recuperados}

INSTRUCCION:
Analiza la seccion del PDA contra cada lineamiento. Para cada lineamiento,
indica:
1. Si la seccion CUMPLE o NO CUMPLE
2. Si no cumple, cual es la regla especifica violada
3. La correccion concreta que se requiere

Responde en formato JSON.
```

---

## Fase 4: Dataset de fine-tuning (Dias 11-14)

**Meta:** Crear los pares instruccion-respuesta para entrenar el modelo.

### Tareas

- [x] **4.1** Definir el formato del dataset (formato Alpaca: instruction, input, output)
- [x] **4.2** Generar 47 pares desde los 4 PDAs reales con `prepare_dataset.py`
- [x] **4.3** Generar outputs via Llama 3.2 con prompt detallado (`generar_outputs.py`)
- [x] **4.4** Revisar y limpiar (pendiente revision fina, dataset usable tal cual)
- [x] **4.5** Dividir en train/validation (90/10): 42 train + 5 validation
- [x] **4.6** Convertir a formato JSONL compatible con SFTTrainer

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| Dataset de entrenamiento | `data/training_dataset.jsonl` |
| Dataset de validacion | `data/validation_dataset.jsonl` |
| Script de preparacion | `src/fine_tuning/prepare_dataset.py` |

### Formato de cada ejemplo

```json
{
  "instruction": "Evalua si la siguiente seccion del PDA cumple con los lineamientos institucionales proporcionados.",
  "input": "SECCION: Resultados de Aprendizaje\nCONTENIDO: [texto real del PDA]\n\nLINEAMIENTOS:\n1. [regla 1]\n2. [regla 2]",
  "output": "{\n  \"seccion\": \"Resultados de Aprendizaje\",\n  \"cumple\": false,\n  \"hallazgos\": [\n    {\n      \"regla\": \"Todo PDA debe incluir al menos 3 resultados de aprendizaje medibles\",\n      \"estado\": \"NO CUMPLE\",\n      \"evidencia\": \"Solo se encontraron 2 resultados de aprendizaje\",\n      \"correccion\": \"Agregar al menos 1 resultado de aprendizaje adicional alineado con las competencias del curso\"\n    }\n  ]\n}"
}
```

### Concepto clave: calidad sobre cantidad

En fine-tuning con datasets pequenos, la calidad de cada ejemplo importa enormemente. Un ejemplo incorrecto puede ensenarle al modelo un patron erroneo que aparecera en multiples inferencias. Es mejor tener 100 ejemplos excelentes que 500 mediocres. Los 20-30 manuales son los mas importantes porque definen el "tono" y la calidad que el self-instruct replicara.

---

## Fase 5: Fine-tuning con QLoRA (Dias 14-17)

**Meta:** Especializar Llama 3.2 3B en verificacion de cumplimiento de PDAs.

### Tareas

- [x] **5.1** Configurar notebook de Google Colab (`notebooks/fine_tuning.ipynb`)
- [x] **5.2** Instalar dependencias: unsloth (incluye transformers, trl, peft, bitsandbytes)
- [x] **5.3** Cargar Llama 3.2 3B con cuantizacion 4-bit via Unsloth
- [x] **5.4** Configurar adaptadores LoRA (r=16, lora_alpha=16, target_modules=attn+mlp, dropout=0.05)
- [x] **5.5** Entrenar con SFTTrainer (3 epochs, lr=2e-4, batch_size=2, gradient_accumulation=4)
- [x] **5.6** Grafica de loss curve incluida en notebook
- [x] **5.7** Guardar adaptador LoRA + exportar a GGUF para ollama
- [x] **5.8** Ejecutar notebook en Colab (entrenamiento completado, loss 1.64->1.26, val 1.52->1.15). Pendiente: descargar GGUF (runtime de Colab se reinicio, re-ejecutar celda 7-8)

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| Notebook de entrenamiento | `notebooks/fine_tuning.ipynb` |
| Adaptador LoRA | `models/lora_adapter/` |
| Metricas de entrenamiento | `results/training_metrics.md` |

### Concepto clave: QLoRA

QLoRA combina dos tecnicas:
1. **Cuantizacion 4-bit (NF4):** Comprime los pesos del modelo de 16 bits a 4 bits. Reduce la memoria de ~6GB a ~2GB para un modelo de 3B parametros. Los pesos originales quedan congelados (no se modifican).
2. **LoRA:** Agrega matrices pequenas entrenables (A y B) a capas especificas del modelo. En vez de actualizar los miles de millones de parametros originales, solo se entrenan estas matrices (~1-5% del total de parametros).

El resultado: fine-tuning de un modelo de 3B parametros en una GPU T4 gratuita de Colab (~16GB VRAM).

### Hiperparametros explicados

| Parametro | Valor | Que controla |
|-----------|-------|-------------|
| `r` | 16 | Rango de las matrices LoRA. Mas alto = mas capacidad de adaptacion, mas memoria |
| `lora_alpha` | 16 | Factor de escala. Generalmente se iguala a r |
| `target_modules` | q_proj, k_proj, v_proj, o_proj | Cuales capas del Transformer reciben adaptadores LoRA |
| `learning_rate` | 2e-4 | Velocidad de aprendizaje. Muy alto = inestable. Muy bajo = no aprende |
| `num_epochs` | 3 | Pasadas completas sobre el dataset. Con datasets pequenos, 3-5 es suficiente |
| `batch_size` | 2 | Ejemplos por paso de gradiente (limitado por VRAM) |
| `gradient_accumulation` | 4 | Simula batch_size efectivo de 8 acumulando gradientes |

---

## Fase 6: Evaluacion e integracion final (Dias 17-21)

**Meta:** Medir el impacto del fine-tuning, integrar todo, y preparar entregables.

### Tareas

- [x] **6.1** Registrar modelo fine-tuneado en ollama (`unibabot-pda`) e integrar al pipeline con seleccion por CLI
- [x] **6.2** Pasar PDAs por el modelo fine-tuneado -- HALLAZGO: loops de generacion, modelo degradado
- [ ] **6.3** Calcular metricas precision/recall/F1 (descartado: el fine-tuneado no produce JSON valido)
- [x] **6.4** Evaluacion humana: rubrica 3 criterios (ES/CA/CX 1-5) sobre 15 hallazgos de m4 -- incluida en IEEE
- [x] **6.5** Comparar baseline vs. fine-tuned: baseline funciona, fine-tuneado degradado por dataset pequeno
- [ ] **6.6** Probar con 1-2 PDAs nuevos (pendiente con baseline)
- [x] **6.7** Documentar decisiones tecnicas, resultados, y limitaciones (`results/evaluation_report.md`)
- [x] **6.8** Actualizar el reporte IEEE con los resultados obtenidos -- `Docs/UnibaBot_PDA.tex` reescrito como paper de resultados (5 paginas, compila sin errores)
- [x] **6.9** Fixes dirigidos para aumentar matching del gold (2026-04-13): Fix C (re-ingest dimension rules + separate LLM eval), Fix B parcial (clarificacion inline de declaraciones informales en prompt), Fix A (targeted strategy mapping + longest-match keyword). Resultado: matched 41/48 → 45/48 manteniendo accuracy 1.000. Tags: `m8a_dimension_ingest`, `m8b_seccion_mapping`. 3 entradas restantes (COMP-102, COMP-105, COMP-119) requieren cambios arquitectonicos.

### Entregables

| Artefacto | Ubicacion |
|-----------|-----------|
| Reporte de evaluacion | `results/evaluation_report.md` |
| Tabla comparativa | `results/baseline_vs_finetuned.md` |
| Script del agente final | `src/agent.py` |
| Reporte IEEE actualizado | `Docs/UnibaBot_PDA.tex` |

### Metricas de evaluacion

| Metrica | Que mide | Como se calcula |
|---------|----------|-----------------|
| Precision | De los problemas que detecto, cuantos son reales | verdaderos_positivos / (verdaderos_positivos + falsos_positivos) |
| Recall | De los problemas reales, cuantos detecto | verdaderos_positivos / (verdaderos_positivos + falsos_negativos) |
| F1 | Balance entre precision y recall | 2 * (precision * recall) / (precision + recall) |
| Evaluacion humana | Calidad general del reporte (claridad, utilidad, correccion) | Escala 1-5 por evaluador humano |

---

## Estructura final del proyecto

```
Unibabot_PDA/
  src/
    pdf_parser.py              # Extraccion y segmentacion de PDAs
    agent.py                   # Pipeline completo del agente
    prompts/
      compliance_prompt.txt    # Template del prompt de evaluacion
    rag/
      ingest.py                # Carga lineamientos en ChromaDB
      vector_store.py          # Configuracion de ChromaDB
      retriever.py             # Busqueda semantica
    fine_tuning/
      prepare_dataset.py       # Crear y formatear dataset
      train.py                 # Script de entrenamiento (mirror del notebook)
      evaluate.py              # Metricas de evaluacion
  data/
    pdas/                      # PDAs reales en PDF
    lineamientos/
      reglas.json              # Lineamientos codificados
    training_dataset.jsonl     # Dataset de entrenamiento
    validation_dataset.jsonl   # Dataset de validacion
  models/
    lora_adapter/              # Adaptador LoRA entrenado
  notebooks/
    fine_tuning.ipynb          # Notebook para Colab
  results/
    baseline_evaluation.md     # Resultados sin fine-tuning
    training_metrics.md        # Curvas y metricas de entrenamiento
    evaluation_report.md       # Resultados con fine-tuning
    baseline_vs_finetuned.md   # Tabla comparativa
  tests/
    test_pdf_parser.py         # Tests de extraccion
    test_retriever.py          # Tests de retrieval
  JSON_archives/               # Datos estructurados existentes
  Docs/                        # Documentacion existente
  ROADMAP.md                   # Este archivo
  CLAUDE.md                    # Instrucciones del proyecto
  requirements.txt             # Dependencias Python
  .gitignore                   # Ya existe
```

---

## Resumen de fases

| Fase | Dias | Meta | Entregable clave |
|------|------|------|------------------|
| 0 | 1-3 | Datos y entorno | PDAs + lineamientos + ollama funcionando |
| 1 | 3-5 | Extraccion de PDF | `pdf_parser.py` -- PDF a texto segmentado |
| 2 | 5-8 | RAG | `retriever.py` -- busqueda semantica de lineamientos |
| 3 | 8-11 | Pipeline baseline | `agent.py` -- primera version end-to-end |
| 4 | 11-14 | Dataset | `training_dataset.jsonl` -- 100-200+ ejemplos |
| 5 | 14-17 | Fine-tuning | Adaptador LoRA entrenado en Colab |
| 6 | 17-21 | Evaluacion | Reporte final con metricas comparativas |

---

## Dependencias entre fases

```
Fase 0 (datos + entorno)
  |
  +--> Fase 1 (extraccion PDF) --requiere PDAs reales
  |       |
  |       v
  +--> Fase 2 (RAG) --requiere lineamientos codificados
          |
          v
        Fase 3 (pipeline baseline) --requiere Fase 1 + Fase 2
          |
          v
        Fase 4 (dataset) --requiere pipeline funcional + evaluaciones manuales
          |
          v
        Fase 5 (fine-tuning) --requiere dataset listo
          |
          v
        Fase 6 (evaluacion) --requiere modelo fine-tuneado + baseline
```

Nota: Las Fases 1 y 2 pueden avanzarse en paralelo una vez que la Fase 0 este lista.

---

## Iteraciones post-roadmap (m7 - m17)

El roadmap original (Fases 0-6) se cerro con el reporte IEEE entregado. Despues vinieron iteraciones adicionales que llevaron al sistema a produccion. Estas se documentan en detalle en `Docs/secciones/11_historial_mejoras.md` y `results/accuracy_progression.md`. Resumen:

| Iteracion | Cambio principal | Resultado clave |
|-----------|------------------|-----------------|
| m7 | Fine-tuning QLoRA Llama 3.2 3B | DESCARTADO (loops de generacion, dataset insuficiente) |
| m8 | Rule-based hybrid (11 EST en Python puro) | +57.6 accuracy points |
| m11 | Rule-driven (despacho explicito reemplaza retrieval semantico) | Cobertura 100% (38/55 -> 55/55) |
| m12 | Qwen 2.5 14B reemplaza Llama 3.1 8B | Mejor precision en espanol y JSON |
| m13 | Extractor + matcher deterministico (LLM solo extrae) | 3-4x mas rapido, recall NC 1.000 |
| m14 | Docling reemplaza PyMuPDF | Tablas preservadas, parsing robusto |
| m15 | Extraccion enriquecida con evidencia + validador anti-alucinacion | **Train AND test 1.000** |
| m16 | Infraestructura: structlog + excepciones tipadas + ollama wrapper con timeout | Sin regresion, observabilidad production-ready |
| **m17** | **Enrichment LLM opt-in (correcciones prescriptivas + resumenes oficina/docente) con cache idempotente** | **Sin regresion en metricas; UX accionable activable via flags --enriquecer y --resumen** |

### m17 — Enrichment LLM (post-evaluacion)

m17 anade dos comportamientos opt-in que NO cambian el motor de cumplimiento:

1. **Correcciones enriquecidas:** una llamada LLM por hallazgo NO CUMPLE produce texto prescriptivo con codigo literal entre comillas y posicion exacta dentro del PDA. Anti-alucinacion: el prompt incluye el contenido real de la seccion como contexto de estilo.
2. **Resumenes ejecutivo + didactico:** una llamada LLM al final genera dos textos con audiencias diferenciadas. "oficina" (3-4 frases, tercera persona, decision rapida); "docente" (4-6 frases, segunda persona formal, didactico).

Ambos cacheados en disco con SHA-256 sobre `(modelo, prompt, inputs)`. Esto da idempotencia bit-a-bit cuando nada cambia y cache miss limpio cuando se edita el prompt. Defaults `False` en `analizar_pda()`: `evaluate.py` y batch runs no pagan latencia extra.

Ver `Docs/secciones/15_enrichment_llm.md` para detalles tecnicos completos.
