<!-- generated-by: gsd-doc-writer -->
# Arquitectura de UnibaBot PDA

## Vision general y filosofia de diseno

UnibaBot PDA es un agente de verificacion de cumplimiento normativo de Planes de Desarrollo Academico (PDA). Recibe un PDA en formato PDF y produce un reporte estructurado que indica, regla por regla, si el documento cumple con los lineamientos institucionales de la Universidad de Ibague.

La arquitectura actual (m13) se sustenta en tres principios fundamentales:

1. **El LLM hace extraccion, no razonamiento de cumplimiento.** Los modelos de lenguaje son buenos extrayendo informacion estructurada de texto no estructurado (encontrar codigos `C1`, `SP5`, `D4` en un documento). Son inconsistentes cuando se les pide razonar sobre si una regla se cumple o no. La arquitectura separa estas dos responsabilidades.

2. **Cobertura 100% por construccion.** El pipeline anterior (RAG semantico) recuperaba las reglas que parecian mas relevantes, dejando sin evaluar aquellas que la busqueda vectorial no priorizaba. El despacho deterministico por metadata garantiza que todas las reglas aplicables al curso sean evaluadas.

3. **Auditabilidad completa.** Cada hallazgo en el reporte cita exactamente: el `regla_id`, los codigos encontrados por el extractor, y los codigos requeridos por la regla. No hay caja negra.

---

## Pipeline de 6 pasos (m13)

```
PDF del PDA
    |
    v
[1] pdf_parser.py          Extraccion y segmentacion
    |                      PyMuPDF + SECCIONES_CONOCIDAS (bilingue)
    v
{secciones: contenido}
    |
    +---> [2] estructural_checker.py    11 checkers deterministicos (EST-001..EST-011)
    |                                   ~100ms, sin LLM
    |
    +---> [3] rule_dispatcher.py        Mapeo de 168 reglas de competencias a secciones
    |         |                         por nombre + fallback por keywords
    |         v
    |     {seccion_pda: [reglas]}
    |
    +---> [4] declaracion_extractor.py  1 llamada al LLM (Qwen 2.5 14B)
    |         |                         Extrae codigos declarados (C1, 1b, SP5, D4, ABET X.Y)
    |         v
    |     {competencias_especificas, competencias_genericas,
    |      saber_pro, dimensiones, abet}
    |
    +---> [5] declaracion_checker.py    Matcher deterministico
    |         |                         Regex por tipo + interseccion de conjuntos
    |         v
    |     [hallazgos de cumplimiento, 100% reproducibles]
    |
    v
[6] agent.py               Consolidacion del reporte
                           results/reporte_<modelo>.json
```

### Paso 1: Extraccion y segmentacion de PDF (`src/pdf_parser.py`)

**Responsabilidad:** Convertir el PDF del PDA en un diccionario `{nombre_seccion: contenido_texto}`.

**Flujo interno:**
```
fitz.open(pdf_path)
    -> page.get_text("dict")          # modo dict: metadata de fuente incluida
    -> bloques con {text, page, font_size, is_bold}
    -> es_encabezado(bloque)          # doble filtro: visual + nombre conocido
    -> segmentar_por_secciones()      # acumula contenido entre encabezados
    -> {seccion: contenido}
```

**Decisiones de diseno:**
- PyMuPDF con modo `"dict"` provee metadata de fuente por span (tamano, bold), no solo texto plano. Esto es necesario para el doble filtro de deteccion de encabezados.
- El doble filtro requiere: (a) que el bloque parezca encabezado visualmente (`font_size > promedio * 1.2` o `is_bold`), y (b) que su texto normalizado contenga alguna entrada de `SECCIONES_CONOCIDAS`.
- `SECCIONES_CONOCIDAS` es una lista bilingue (espanol/ingles) de ~30 patrones que cubre variantes como `"estrategia pedagogica"` y `"pedagogical strategy"`.
- La funcion `normalizar()` quita acentos, numeros de seccion iniciales y pasa a minusculas, tolerando variantes como `"1. Informacion general"` y `"Informacion General del Curso"`.
- El primer bloque antes de cualquier encabezado se almacena como `"PREAMBULO"` y se descarta en etapas posteriores.

**Limitaciones:**
- PDAs con tablas complejas pueden generar bloques de texto fragmentados.
- No soporta PDAs escaneados como imagen (requeriria OCR).
- Campos de tabla que sean bold y cortos pueden pasar el filtro si coinciden con una seccion conocida.

---

### Paso 2: Verificacion estructural determinista (`src/rules/estructural_checker.py`)

**Responsabilidad:** Evaluar las 11 reglas estructurales (EST-001 a EST-011) mediante logica Python pura, sin consultar el LLM.

**Las 11 reglas:**

| Regla | Descripcion |
|-------|-------------|
| EST-001 | Informacion general con programa, nombre, tipo, modalidad |
| EST-002 | Al menos una estrategia pedagogica declarada |
| EST-003 | Contexto de la asignatura presente |
| EST-004 | Descripcion y proposito del curso |
| EST-005 | Resultados de Aprendizaje Esperados (RAE) |
| EST-006 | Competencias especificas, genericas, SABER PRO y dimensiones |
| EST-007 | Criterios de valoracion con porcentajes y fechas |
| EST-008 | Cronograma de actividades con estructura temporal |
| EST-009 | Bibliografia de referencia |
| EST-010 | Politicas y acuerdos para el buen funcionamiento |
| EST-011 | Fecha del encuadre pedagogico + seccion de firmas |

**Mecanismo:** Cada funcion `check_EST_XXX(secciones)` usa `find_seccion()` o `find_seccion_fallback()` para localizar la seccion objetivo. `find_seccion_fallback()` es mas tolerante: si no encuentra match por nombre de seccion, busca los keywords objetivo en el contenido de cualquier seccion (util para PDAs con estructura atipica).

**Salida:** Lista de hallazgos con el formato estandar `{regla_id, regla, estado, evidencia, correccion}`.

---

### Paso 3: Despacho de reglas por seccion (`src/rag/rule_dispatcher.py`)

**Responsabilidad:** Dado un codigo de curso, determinar que reglas de competencias aplican y a que seccion real del PDA corresponde cada una.

**Flujo:**
```
reglas.json (179 reglas totales)
    -> filtrar: tipo != "estructural" AND aplica_a IN (codigo_curso, "todos")
    -> para cada regla: encontrar_seccion_destino(regla, secciones_pda)
    -> agrupar por seccion destino
    -> {seccion_real: [reglas_aplicables]}
```

**Estrategia de localizacion en 2 pasos:**
1. Match por nombre via `MAPPING_SECCIONES` invertido: busca si el nombre normalizado de alguna seccion del PDA contiene un keyword que mapee al `seccion_pda` target de la regla.
2. Fallback por contenido: si ningun nombre matchea, busca keywords del tipo de seccion dentro del texto de cada seccion. La seccion con mayor numero de keywords coincidentes gana (umbral: >= 2).

Las reglas cuya seccion destino no existe en el PDA se agrupan bajo la clave `"__seccion_no_presente__"`, lo que dispara hallazgos `NO CUMPLE` deterministicos en el orquestador.

**Por que se reemplazo el retrieval semantico:** El retrieval vectorial (ChromaDB) priorizaba las reglas con mayor similitud semantica al texto de la seccion, dejando sin evaluar reglas aplicables que tuvieran menor similitud. El despacho por metadata garantiza cobertura 100%: si la regla aplica al curso (segun `aplica_a` en `reglas.json`), se evalua sin excepcion.

---

### Paso 4: Extraccion de declaraciones via LLM (`src/rules/declaracion_extractor.py`)

**Responsabilidad:** Extraer los codigos canonicos declarados en el PDA mediante una sola llamada al LLM.

**Flujo:**
```
secciones del PDA
    -> _seleccionar_texto_relevante()    # filtra por keywords de nombre + fallback por contenido
    -> extraccion_prompt.txt + texto_pda
    -> ollama.chat(qwen2.5:14b, temperature=0.0, num_predict=600)
    -> _extraer_json_de_respuesta()      # tolerante a markdown ```json``` y {{...}}
    -> _limpiar_declaraciones()          # filtra codigos invalidos (alucinaciones)
    -> {competencias_especificas, competencias_genericas, saber_pro, dimensiones, abet}
```

**Seleccion de texto relevante:** Se incluyen secciones cuyo nombre contiene keywords como `"competencia"`, `"resultado"`, `"rae"`, `"estrategia"`, `"dimension"`, etc. (bilingue). Si una seccion no matchea por nombre pero su contenido contiene codigos canonicos literales (patron `\b(C[1-9]|SP[1-5]|D[1-6]|1[a-l])\b`), tambien se incluye. Las secciones de bibliografia, cronograma y firmas se excluyen siempre.

**Codigos validos reconocidos:**
- Competencias especificas: `C1`, `C2`, `C3`
- Competencias genericas: `1a` a `1l`
- SABER PRO: `SP1` a `SP5`
- Dimensiones: `D1` a `D6`
- ABET: formato `X.Y` (ej: `5.1`, `1.3`)

El prompt incluye tres ejemplos (few-shot): declaracion literal de codigos, declaracion por nombre canonico (ej: "Dimension Internacional" -> `D4`), e inferencias NO autorizadas para anclar el comportamiento.

**Fallback robusto:** Si el LLM falla o devuelve JSON invalido, se retornan listas vacias. Es mejor reportar "no declarado" que alucinaciones.

---

### Paso 5: Matcher deterministico (`src/rules/declaracion_checker.py`)

**Responsabilidad:** Comparar los codigos declarados (obtenidos del extractor) contra los codigos requeridos por cada regla aplicable. Cero llamadas al LLM.

**Mecanismo:**
```
para cada regla en reglas_canonicas:
    codigo_requerido = extraer_codigo_de_regla(regla)  # regex sobre regla.descripcion
    key = TIPO_A_KEY[regla.tipo]                        # e.g. "dimension" -> "dimensiones"
    declarados = set(declaraciones[key])
    cumple = codigo_requerido in declarados
    -> hallazgo(regla_id, estado, evidencia, correccion)
```

**Extraccion del codigo requerido:** `extraer_codigo_de_regla()` aplica patrones regex por tipo sobre la descripcion de la regla. Por ejemplo, para tipo `"dimension"`, el patron `r"dimension\s+(D\d+)"` extrae `D4` de `"debe declarar la dimension D4: Internacional"`.

**Auditabilidad:** La evidencia de cada hallazgo cita los codigos declarados encontrados (`sorted(declarados)`) y el codigo buscado, permitiendo trazabilidad completa.

---

### Paso 6: Consolidacion del reporte (`src/agent.py`)

**Responsabilidad:** Orquestar los 5 pasos anteriores y producir el reporte JSON final.

**Estructura del reporte:**
```json
{
  "archivo": "PDAs/ejemplo.pdf",
  "modelo": "qwen2.5:14b",
  "codigo_curso": "22A14",
  "total_secciones": 0,
  "resultados": [
    {"seccion": "__estructural_global__", "hallazgos": [...]},
    {"seccion": "__declaraciones_global__", "hallazgos": [...]},
    {"seccion": "__seccion_ausente_global__", "hallazgos": [...]}
  ]
}
```

Los hallazgos individuales siguen el schema Pydantic definido en `src/schemas.py`:
```python
class Hallazgo(BaseModel):
    regla_id: str
    regla: str
    estado: Literal["CUMPLE", "NO CUMPLE"]
    evidencia: str
    correccion: str | None
```

**Comportamiento cuando `codigo_curso` no se provee:** El sistema ejecuta el pipeline estructural (paso 2) pero omite el extractor+matcher (pasos 4-5). En ese modo, el LLM compliance legacy puede usarse como fallback, aunque en la practica las 168 reglas de competencias tienen todas codigo canonico y el fallback queda vacio.

**Reportes guardados en:** `results/reporte_<modelo>.json` (ej: `results/reporte_qwen2.5-14b.json`)

**Interfaz de progreso:** `analizar_pda()` acepta un callback `on_progress(evento, datos)` que la CLI usa para imprimir stdout y la UI de Streamlit usa para actualizar el estado visual. Los eventos emitidos son: `parsing_start`, `parsing_done`, `structural_start`, `structural_done`, `extract_start`, `extract_done`, `llm_prep_start`, `llm_prep_done`, `section_eval_start`, `section_eval_done`, `done`.

---

## Infraestructura ChromaDB / RAG (modo opt-in)

Los modulos `src/rag/ingest.py`, `src/rag/retriever.py`, `src/rag/embeddings.py` y `src/rag/reranker.py` **no forman parte del pipeline por defecto** desde m11. Se mantienen para experimentos.

| Modulo | Funcion | Estado |
|--------|---------|--------|
| `rag/ingest.py` | Carga `reglas.json` en ChromaDB (cosine similarity) | Opt-in |
| `rag/retriever.py` | Busqueda semantica top-k con filtros por seccion | Opt-in |
| `rag/embeddings.py` | Funcion de embeddings SBERT personalizada | Opt-in |
| `rag/reranker.py` | Cross-encoder reranker sobre resultados del retriever | Opt-in |

La base vectorial se persiste en `data/chroma_db/` (gitignored). Para activarla es necesario ejecutar `python src/rag/ingest.py` antes de usar `retriever.py`.

El mapping `src/rag/seccion_mapping.py` si es parte del pipeline activo: lo usa `rule_dispatcher.py` para traducir nombres de secciones detectadas por el parser a categorias canonicas de `seccion_pda`.

---

## Fuentes de datos y generacion de reglas

### reglas.json (`data/lineamientos/reglas.json`)

El archivo de reglas tiene 179 entradas generadas por `src/generar_reglas.py` a partir de los archivos fuente en `JSON_archives/`:

| Archivo fuente | Contenido |
|----------------|-----------|
| `cursos.json` | Codigo a nombre de cada materia |
| `competenciascursos.json` | Que competencias requiere cada materia |
| `competencias.json` | Descripcion de cada competencia por codigo |
| `abet.json` | Indicadores ABET en ingles |
| `abet_es.json` | Indicadores ABET en espanol |

**Tipos de reglas generadas:**
- **Estructurales (11):** Secciones obligatorias en todo PDA, definidas manualmente en el script.
- **De competencias (168):** Generadas automaticamente, una por cada par (curso, competencia requerida). Cubren competencias especificas, genericas, SABER PRO, dimensiones e indicadores ABET.

Cada regla tiene la forma:
```json
{
  "id": "COMP-003",
  "tipo": "competencia_generica",
  "descripcion": "El PDA debe declarar la competencia generica 1g: Aprender a aprender",
  "seccion_pda": "Competencias / Resultados de Aprendizaje",
  "aplica_a": "22A14"
}
```

### Dataset gold (`data/gold_labels.json`, `data/gold_labels_test.json`)

| Archivo | Split | Entradas | PDAs |
|---------|-------|----------|------|
| `gold_labels.json` | Train | 57 | 3 |
| `gold_labels_test.json` | Test hold-out | 55 | 3 |

Los gold labels fueron generados con el pipeline `src/tooling/` y anotados con Claude.

---

## Diagrama de flujo de datos completo

```
JSON_archives/
  cursos.json
  competenciascursos.json   ---> src/generar_reglas.py ---> data/lineamientos/reglas.json
  competencias.json                                               |
  abet.json                                                       |
  abet_es.json                                                    |
                                                                  |
                                          +------------------------+
                                          |                        |
                                          v                        v
PDAs/*.pdf                     src/rag/rule_dispatcher.py    src/rules/estructural_checker.py
    |                          (168 reglas no-EST)           (11 reglas EST)
    v                                     |                        |
src/pdf_parser.py                         |                        |
    |                                     v                        v
    +------> {secciones}  +--------> [reglas por seccion]    [hallazgos EST]
    |                     |              |
    |                     |              v (paso 4+5, si codigo_curso provisto)
    |                     |   src/rules/declaracion_extractor.py
    |                     |         (1 LLM call, Qwen 2.5 14B)
    |                     |              |
    |                     |              v
    |                     |   src/rules/declaracion_checker.py
    |                     |         (regex + set intersection)
    |                     |              |
    +--------------------------------------------------+
                                         |
                                         v
                                    src/agent.py
                                         |
                                         v
                              results/reporte_<modelo>.json
```

---

## Rendimiento (m13)

| Etapa | Tiempo por PDA |
|-------|---------------|
| Extraccion PDF | ~1s |
| Verificacion estructural | ~100ms |
| Despacho de reglas | ~50ms |
| Extraccion de declaraciones (LLM) | ~20s |
| Matching deterministico | <10ms |
| **Pipeline completo** | **~30s** |
| Evaluacion 3 PDAs completos | ~95-120s |

El pipeline m13 es 3-4x mas rapido que m12 (120-140s por PDA) principalmente por reducir N llamadas LLM por seccion a 1 llamada LLM por PDA.

---

## Metricas de evaluacion (m13 final)

| Split | Accuracy | Precision NC | Recall NC | Matched |
|-------|----------|--------------|-----------|---------|
| Train (57 entradas, 3 PDAs) | 0.965 | 1.000 | 0.500 | 57/57 |
| Test hold-out (55 entradas, 3 PDAs) | 0.982 | 0.900 | 1.000 | 55/55 |

- **Precision NC = 1.000 en train:** Cero falsos positivos (el sistema no reporta incumplimiento donde no lo hay).
- **Recall NC = 1.000 en test:** El sistema detecta el 100% de los incumplimientos reales en PDAs no vistos.
- **Matched = 100%:** Todas las entradas gold son evaluadas (cobertura total, sin entradas sin match).

Ejecutar la evaluacion:
```bash
# Train set
python src/evaluate.py --tag m13

# Test hold-out
python src/evaluate.py --tag m13_test --gold data/gold_labels_test.json
```

---

## Evolucion de la arquitectura

La arquitectura actual es el resultado de 13 iteraciones. Los cambios mas importantes:

### m1-m4: RAG semantico puro
- ChromaDB + sentence-transformers para recuperar los lineamientos mas relevantes.
- LLM (Llama 3.2 3B -> Llama 3.1 8B) para razonar cumplimiento por seccion.
- Accuracy mejoro de 0.351 a ~1.000 pero solo 45/48 gold labels hacian match (3 sin cobertura).
- Problema raiz: el retrieval semantico perdia reglas aplicables con baja similitud coseno.

### m8: Checkers estructurales rule-based
- Las 11 reglas EST se sacaron del pipeline LLM y se implementaron como Python puro.
- Precision/recall perfectos para reglas estructurales.
- Las reglas de competencias seguian usando RAG.

### m11: Inversion arquitectural - despacho por metadata
- `rule_dispatcher.py` reemplaza el retrieval semantico para reglas de competencias.
- Cobertura sube a 57/57 y 55/55 (100%) porque todas las reglas aplicables se evaluan.
- La accuracy aparente baja porque casos dificiles que antes quedaban sin cobertura ahora se evaluan y pueden fallar.

### m12: Upgrade a Qwen 2.5 14B
- Sustitucion de Llama 3.1 8B por Qwen 2.5 14B (vía ollama).
- Precision NC = 1.000 en train (cero falsas alarmas).
- Recall NC +4.8pp en test vs Llama 3.1 8B.

### m13: Extractor + matcher deterministico
- El LLM deja de razonar sobre cumplimiento de competencias.
- Una sola llamada LLM extrae los codigos declarados en el PDA.
- `declaracion_checker.py` determina cumplimiento por interseccion de conjuntos.
- Resultado: 3-4x mas rapido, recall NC = 1.000 en test hold-out, auditabilidad completa.

---

## Puntos de extension

### Agregar una nueva regla estructural

1. Implementar `check_EST_012(secciones)` en `src/rules/estructural_checker.py` siguiendo el patron de los checkers existentes.
2. Agregar la regla a `CHECKERS` al final del archivo.
3. Agregar la entrada correspondiente en `data/lineamientos/reglas.json` con `"tipo": "estructural"`.

### Agregar soporte para un nuevo curso

1. Agregar el curso en `JSON_archives/cursos.json`.
2. Declarar sus competencias requeridas en `JSON_archives/competenciascursos.json`.
3. Regenerar `reglas.json`: `python src/generar_reglas.py`.
4. Agregar el PDA y codigo de curso en `PDAS_CURSOS` de `src/evaluate.py` para incluirlo en la evaluacion.

### Agregar un nuevo tipo de competencia canonico

1. Agregar los codigos validos en `CODIGOS_VALIDOS` de `declaracion_extractor.py`.
2. Agregar el mapeo tipo -> key en `TIPO_A_KEY` de `declaracion_checker.py`.
3. Agregar patrones regex en `PATRONES_CODIGO_POR_TIPO` de `declaracion_checker.py`.
4. Actualizar el prompt `src/prompts/extraccion_prompt.txt` con los nuevos codigos validos y nombres canonicos.

### Agregar un nuevo PDA al dataset gold

1. Colocar el PDF en `PDAs/`.
2. Ejecutar `src/tooling/generar_gold_exhaustivo.py` para generar candidatos.
3. Anotar con `src/tooling/anotar_claude_test.py` (o train segun el split).
4. Fusionar con `src/tooling/fusionar_gold.py`.

---

## Dependencias principales

| Dependencia | Proposito |
|-------------|-----------|
| PyMuPDF (`fitz`) | Extraccion de texto y metadata de PDF |
| ollama | Cliente Python para inferencia local con Qwen 2.5 14B |
| pydantic | Validacion de schema del reporte del LLM |
| ChromaDB | Base de datos vectorial (opt-in, no pipeline default) |
| sentence-transformers | Embeddings para experimentos RAG (opt-in) |
