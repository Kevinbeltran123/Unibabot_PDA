# Benchmark: rule-driven vs RAG semantico

Comparacion empirica head-to-head entre los dos dispatchers que conviven en `src/rag/`. Aisla la variable "como se selecciona el conjunto de reglas a evaluar" manteniendo el resto del pipeline (parser, extractor LLM, matcher determinista, enrichment) identico.

## Metodologia

**Pipeline comun a ambos brazos:**

```
PDF -> pdf_parser (Docling) -> rules/estructural_checker (11 EST)
                            -> rules/declaracion_extractor (1 LLM call por PDA)
                            -> rules/declaracion_checker (regex + set intersection)
                            -> reporte JSON
```

**Lo unico que cambia:**

| Paso | Rule-driven (`dispatcher="rule"`) | RAG semantico (`dispatcher="rag"`) |
|------|------------------------------------|------------------------------------|
| Como se obtiene el conjunto de reglas a evaluar | `reglas_aplicables(codigo_curso)`: itera `reglas.json` y devuelve todas las reglas con `aplica_a in (curso, "todos")`. Cobertura 100% por construccion. | `recuperar_reglas_aplicables(secciones, codigo_curso, top_k=5)`: para cada seccion del PDA consulta ChromaDB con SBERT multilingue + cross-encoder reranker. Une los top-k de cada seccion. Reglas fuera del top-k jamas se evaluan. |

**Modelo LLM:** Qwen 2.5 14B (mismo en ambos brazos).
**Hardware:** MacBook Pro M3 18GB.
**Top-k RAG:** 5 (default historico m4-m10).
**Reranker:** activo (`use_reranker=True`).

**Datasets:**
- Train: `data/gold_labels.json` — 51 entradas, 3 PDAs (22A14, 22A12, 22A31).
- Test (hold-out): `data/gold_labels_test.json` — 55 entradas, 3 PDAs nuevos (22A32, 22A35, 22A52).

**Sesgo conocido:** El gold dataset se construyo iterando sobre el rule-driven dispatcher, lo cual lo sesga estructuralmente: las entradas que el rule-driven nunca generaria (ej: una regla aplicable que no se traduce a un hallazgo) tampoco entran al gold. Por eso el RAG arrancara con desventaja en cobertura. Este informe lo reporta explicitamente como "matched / total" y separa accuracy (sobre matched) de coverage (matched / total) para no contaminar las metricas.

## Resultados

### Train (51 entradas, 3 PDAs: 22A12, 22A14, 22A31)

| Metrica | Rule-driven | RAG semantico (top-k=5) | Delta |
|---------|-------------|-------------------------|-------|
| Accuracy (sobre matched) | **1.000** | **1.000** | =  |
| Precision NO CUMPLE | **1.000** | **0.000***  | -1.000 |
| Recall NO CUMPLE | **1.000** | **0.000***  | -1.000 |
| Cobertura (matched / 51) | **51 / 51 (100.0%)** | **45 / 51 (88.2%)** | -6 reglas |
| not_found | 0 | 6 | +6 |
| Latencia total (3 PDAs) | 153.6 s | 147.9 s | -3.7% (RAG ligeramente mas rapido) |

\*La unica entrada NO CUMPLE del gold train (`COMP-119`, curso 22A31) cae dentro de las 6 que el RAG no recupera. Por construccion no genera TP ni FP, por lo que precision y recall colapsan a 0/0. Rule-driven la captura, la matchea y la reporta correctamente.

### Test hold-out (55 entradas, 3 PDAs nuevos: 22A32, 22A35, 22A52)

| Metrica | Rule-driven | RAG semantico (top-k=5) | Delta |
|---------|-------------|-------------------------|-------|
| Accuracy (sobre matched) | **1.000** | **1.000** | =  |
| Precision NO CUMPLE | **1.000** | **1.000** | =  |
| Recall NO CUMPLE | **1.000** | **1.000** | =  |
| Cobertura (matched / 55) | **55 / 55 (100.0%)** | **48 / 55 (87.3%)** | -7 reglas |
| not_found | 0 | 7 | +7 |
| Latencia total (3 PDAs) | 161.4 s | 158.9 s | -1.5% |

En test el RAG mantiene precision/recall NC = 1.000 porque las 7 entradas NC reales SI fueron recuperadas. Pero pierde 7 entradas CUMPLE (todas en cursos 22A32 y 22A52) que el rule-driven SI evalua y reporta correctamente.

### Detalle de las 13 entradas que el RAG nunca evalua

| Split | regla_id | curso | PDA | Seccion del PDA | estado_esperado | Causa probable |
|-------|----------|-------|-----|-----------------|-----------------|----------------|
| train | COMP-105 | 22A14 | Intelligent Agents | "Classroom typology" | CUMPLE | Seccion en ingles, embedding lejos del vocabulario abstracto de la regla |
| train | COMP-119 | 22A31 | Desarrollo UIUX | "Competencias genéricas:" | **NO CUMPLE** | top-k=5 saturado por otras reglas de la misma seccion |
| train | COMP-120..123 | 22A31 | Desarrollo UIUX | "Competencias genéricas:" | CUMPLE (x4) | Idem: seccion con muchas reglas applicables, top-k satura |
| test | COMP-107..115 | 22A32 | Gestion TI | "Competencias / Resultados de Aprendizaje" | CUMPLE (x6) | Seccion grande con muchas reglas applicables; top-k=5 deja afuera al menos 6 |
| test | COMP-006 | 22A52 | Pensamiento Computacional | "Competencias" | CUMPLE | Idem |

**Patron unico:** todas las perdidas vienen de **secciones donde el numero de reglas applicables al curso > top_k**. El reranker no resuelve esto: solo re-ordena dentro del top_k del retriever inicial. Subir top_k mitiga pero no elimina (curso 22A32 tiene 10 reglas en una seccion, top_k tendria que ser >=10 para garantizar cobertura — y entonces el costo crece linealmente y el ranking semantico deja de tener sentido).

## Caso de estudio: PDA bilingue (22A14, "Intelligent Agents")

Este PDA tiene secciones cuyo encabezado esta en ingles ("Pedagogical Strategy(ies)", "Classroom typology"). Historicamente fue el caso donde el retriever semantico mas perdio cobertura. Smoke test ejecutado antes del benchmark formal:

| Dispatcher | EST hallazgos | COMP declaraciones | Total |
|------------|---------------|--------------------|-------|
| Rule-driven | 11 | 6 | 17 |
| RAG semantico (top-k=5) | 11 | 5 | 16 |

La regla perdida es **COMP-105** (Dimension D4 Internacional, declarada en seccion "Classroom typology"). El retriever no la rankea en el top-5 de ninguna seccion porque el embedding de la regla ("Dimension D4: Internacional") queda lejos del embedding del contenido en ingles. Rule-driven evalua la regla sin consultar embeddings: la encuentra via fallback por keywords en `rule_dispatcher.encontrar_seccion_destino`.

## Costos de setup

| Concepto | Rule-driven | RAG semantico |
|----------|-------------|---------------|
| Datos persistidos en disco | `data/lineamientos/reglas.json` (60 KB) | `data/chroma_db/` (1.1 MB) + el JSON anterior |
| Dependencias adicionales | (ninguna) | `chromadb>=0.5.0`, `sentence-transformers>=3.0.0`, `torch>=2.0.0` |
| Setup inicial | (ninguno; lee el JSON al vuelo) | `python src/rag/ingest.py` (~30s, descarga modelo SBERT primera vez) |
| Re-indexacion al editar reglas | Ninguna; el JSON se relee en cada corrida | Re-ejecutar `ingest.py` (varios segundos por chunk) |
| Modelo de embeddings al cargar | (ninguno) | SBERT `all-MiniLM-L6-v2` (~80 MB en RAM) + cross-encoder multilingue (~280 MB) |

## Escalabilidad teorica

Sea N el numero de reglas y S el numero de secciones del PDA.

| Operacion | Rule-driven | RAG semantico |
|-----------|-------------|---------------|
| Cargar reglas a memoria | O(N) una vez por proceso | O(N) ingesta inicial; O(1) recall en queries |
| Filtrar reglas para un curso | O(N) lookup directo en lista | O(N) filter en metadata + O(top_k) ranking semantico |
| Despachar reglas a secciones | O(N x S) match por nombre + keyword fallback | O(S x retrieve_k x emb_dim) por embedding query + reranker |
| Anadir una nueva regla | O(1): editar JSON, listo | Re-ejecutar `ingest.py` (re-embedding del corpus completo si cambia el modelo, parcial si solo agrega) |
| Crecimiento esperable a 1000 reglas | Misma latencia | Latencia crece linealmente con N en el filter; O(log N) en el ANN search |

**Implicacion:** rule-driven escala mejor en mantenimiento (anadir reglas no requiere re-procesar el corpus) y latencia (no paga el costo del embedding query por seccion). RAG semantico solo seria preferible si el catalogo de reglas creciera al punto en que iterar sobre todas las aplicables a un curso fuera prohibitivo (>10K reglas/curso, escenario fuera del alcance del proyecto).

## Conclusiones

1. **Cobertura es el diferenciador, no la calidad del veredicto.** Sobre las entradas del gold que ambos dispatchers evaluan, accuracy es 1.000 en ambos brazos. Pero el RAG semantico pierde 13 entradas (6 en train + 7 en test) que el rule-driven SI evalua. La perdida critica: la unica entrada NO CUMPLE del split train (`COMP-119`, curso 22A31) cae dentro de las 6 que el RAG no recupera.

2. **El cuello de botella del RAG es estructural, no resoluble con tuning.** Las 13 perdidas siguen un solo patron: secciones del PDA donde el numero de reglas applicables al curso supera `top_k=5`. El reranker no ayuda (re-ordena dentro del top-k del bi-encoder, no expande el conjunto). Subir top_k mitiga pero no escala: el curso 22A32 tiene 10 reglas en una sola seccion; garantizar cobertura requeriria top_k >= 10 por seccion, lo que neutraliza el ranking semantico.

3. **Costos operacionales del rule-driven:** elimina ~360 MB de modelos en RAM (SBERT bi-encoder + cross-encoder reranker), una base vectorial de 1.1 MB en disco, y las dependencias `torch`, `sentence-transformers`, `chromadb`. Para los volumenes del proyecto (179 reglas, 23 cursos) el rule-driven es estrictamente dominante.

4. **Latencia comparable en este volumen.** A 179 reglas y ~10 secciones por PDA el costo del embedding query por seccion es comparable al del lookup en lista. La diferencia se haria notoria solo en escalas mayores donde rule-driven mantiene su latencia constante mientras RAG paga `S x retrieve_k x emb_dim` por PDA.

5. **Cuando reconsiderarlo:** rule-driven domina mientras N (reglas) sea pequeno y el catalogo cambie con baja frecuencia. RAG semantico solo seria preferible si el catalogo creciera a miles de reglas Y se quisiera hacer query natural-language sobre las reglas (no solo evaluacion contra PDAs estructurados). Para el alcance institucional de UnibaBot (catalogo finito, version-controlado en JSON) rule-driven es la decision arquitectonica correcta.

## Reproducibilidad

```bash
# Re-ingestar reglas en ChromaDB (necesario para el camino RAG)
python src/rag/ingest.py

# Benchmark train
python src/evaluate.py --tag bench_rule_train --dispatcher rule --gold-path data/gold_labels.json
python src/evaluate.py --tag bench_rag_train --dispatcher rag --gold-path data/gold_labels.json

# Benchmark test
python src/evaluate.py --tag bench_rule_test --dispatcher rule --gold-path data/gold_labels_test.json
python src/evaluate.py --tag bench_rag_test --dispatcher rag --gold-path data/gold_labels_test.json

# Comparar dos runs guardados
python src/evaluate.py --compare bench_rule_train bench_rag_train
```

Las metricas se persisten en `results/metrics_<tag>.json`. Los reportes crudos en `results/reports_<tag>.json`.
